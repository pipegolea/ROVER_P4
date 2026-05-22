from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, Response
import csv, os, json, threading, time
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "rover_asme_2025_secret_key_xyz!")

# ── Credenciales de los 8 grupos ──────────────────────────────────────────────
GROUPS = {
    "admin":  {"password": "Proyecto4",      "name": "Admin"},
    "grupo1": {"password": "rover01_202610",  "name": "grupo1"},
    "grupo2": {"password": "rover02_202610",  "name": "grupo2"},
    "grupo3": {"password": "rover03_202610",  "name": "grupo3"},
    "grupo4": {"password": "rover04_202610",  "name": "grupo4"},
    "grupo5": {"password": "rover05_202610",  "name": "grupo5"},
    "grupo6": {"password": "rover06_202610",  "name": "grupo6"},
    "grupo7": {"password": "rover07_202610",  "name": "grupo7"},
    "grupo8": {"password": "rover08_202610",  "name": "grupo8"},
}

DATA_DIR  = os.environ.get("DATA_DIR", "/tmp")
DATA_FILE = os.path.join(DATA_DIR, "resultados.csv")
D_TOTAL   = 30.48 ** 3

# ── Crear CSV si no existe ────────────────────────────────────────────────────
def init_csv():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except PermissionError:
        pass
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                "Timestamp","Grupo","Design_Score","Grams","Pieces",
                "Total_Parts","Exceptions","AM_Parts",
                "Width_cm","Length_cm","Height_cm","Volume_cm3",
                "Base_Score","AM_Ratio_pct","Final_Score","Dimension_Penalty"
            ])

init_csv()

# ── Lógica ROVER ──────────────────────────────────────────────────────────────
def calcular_rover(data):
    design   = float(data["design"])
    grams    = float(data["grams"])
    pieces   = float(data["pieces"])
    total_p  = float(data["total_parts"])
    excep    = float(data["exceptions"])
    am_parts = float(data["am_parts"])
    A        = float(data["width"])
    L        = float(data["length"])
    H        = float(data["height"])

    dimension       = L * A * H
    effective_parts = total_p - excep
    penalty_applied = False
    design_used     = design

    if effective_parts <= 0:
        return None, "El total de partes menos excepciones debe ser mayor a 0."
    if am_parts > effective_parts:
        return None, "Las partes AM no pueden superar las partes efectivas."
    if design > 5000:
        return None, "El puntaje de diseño no puede superar 5000."

    if dimension > D_TOTAL:
        delta_dim   = dimension - D_TOTAL
        design_used = design * (D_TOTAL / (D_TOTAL + delta_dim))
        penalty_applied = True

    base_score  = design_used + grams + (pieces * 1000)
    am_ratio    = am_parts / effective_parts
    final_score = am_ratio * base_score

    return {
        "design_used":     round(design_used, 2),
        "grams_pts":       grams,
        "pieces_pts":      pieces * 1000,
        "base_score":      round(base_score, 2),
        "am_parts":        am_parts,
        "effective_parts": effective_parts,
        "am_ratio_pct":    round(am_ratio * 100, 1),
        "final_score":     round(final_score, 2),
        "dimension":       round(dimension, 2),
        "d_total":         round(D_TOTAL, 2),
        "penalty_applied": penalty_applied,
    }, None

# ── Rutas originales ──────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "group" in session:
        return redirect(url_for("calculator"))
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    username = (request.form.get("username","").strip().lower().replace(" ",""))
    password = request.form.get("password","").strip()
    print("========== LOGIN DEBUG ==========")
    print("USERNAME RECIBIDO:", username)
    print("PASSWORD RECIBIDO:", password)
    group = GROUPS.get(username)
    print("GROUP ENCONTRADO:", group)
    if group and group["password"] == password:
        session["group"]      = username
        session["group_name"] = group["name"]
        print("LOGIN EXITOSO")
        if username == "admin":
            return redirect(url_for("ranking"))
        return redirect(url_for("calculator"))
    print("LOGIN FALLIDO")
    return render_template("login.html", error="Usuario o contraseña incorrectos")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/calculator")
def calculator():
    if "group" not in session:
        return redirect(url_for("index"))
    return render_template("calculator.html", group_name=session["group_name"])

@app.route("/calculate", methods=["POST"])
def calculate():
    if "group" not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.get_json()
    result, error = calcular_rover(data)
    if error:
        return jsonify({"error": error}), 400
    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            session["group_name"],
            data["design"], data["grams"], data["pieces"],
            data["total_parts"], data["exceptions"], data["am_parts"],
            data["width"], data["length"], data["height"],
            result["dimension"], result["base_score"],
            result["am_ratio_pct"], result["final_score"], result["penalty_applied"]
        ])
    return jsonify(result)

@app.route("/download_csv")
def download_csv():
    return send_file(DATA_FILE, as_attachment=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ADICIÓN — RANKING EN TIEMPO REAL
# ═══════════════════════════════════════════════════════════════════════════════

RANKING_FILE = os.path.join(DATA_DIR, "ranking.json")
TEAM_NAMES   = ["grupo1","grupo2","grupo3","grupo4","grupo5","grupo6","grupo7","grupo8"]
_sse_clients = []
_sse_lock    = threading.Lock()

def _load_ranking():
    try:
        with open(RANKING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {t: {"score": 0, "updated": ""} for t in TEAM_NAMES}

def _save_ranking(data):
    with open(RANKING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def _sorted_ranking(r):
    return sorted([{"team": k, **v} for k, v in r.items()],
                  key=lambda x: x["score"], reverse=True)

def _push_sse(payload):
    msg = f"data: {json.dumps(payload)}\n\n"
    with _sse_lock:
        for q in list(_sse_clients):
            q.append(msg)

# Init ranking.json
if not os.path.exists(RANKING_FILE):
    _save_ranking({t: {"score": 0, "updated": ""} for t in TEAM_NAMES})

@app.route("/ranking")
def ranking():
    if "group" not in session:
        return redirect(url_for("index"))
    is_admin = (session.get("group") == "admin")
    return render_template("ranking.html",
                           group_name=session["group_name"],
                           is_admin=is_admin,
                           ranking=_sorted_ranking(_load_ranking()))

@app.route("/admin/update_score", methods=["POST"])
def update_score():
    if session.get("group") != "admin":
        return jsonify({"error": "No autorizado"}), 403
    data  = request.get_json()
    team  = data.get("team","").strip()
    score = float(data.get("score", 0))
    if team not in TEAM_NAMES:
        return jsonify({"error": "Equipo no válido"}), 400
    r = _load_ranking()
    r[team] = {"score": score, "updated": datetime.now().strftime("%H:%M:%S")}
    _save_ranking(r)
    sr = _sorted_ranking(r)
    _push_sse(sr)
    return jsonify({"ok": True, "ranking": sr})

@app.route("/admin/reset_score", methods=["POST"])
def reset_score():
    if session.get("group") != "admin":
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    team = data.get("team","").strip()
    if team not in TEAM_NAMES:
        return jsonify({"error": "Equipo no válido"}), 400
    r = _load_ranking()
    r[team] = {"score": 0, "updated": ""}
    _save_ranking(r)
    sr = _sorted_ranking(r)
    _push_sse(sr)
    return jsonify({"ok": True, "ranking": sr})

@app.route("/stream/ranking")
def stream_ranking():
    if "group" not in session:
        return "", 403
    q = []
    with _sse_lock:
        _sse_clients.append(q)
    def generate():
        yield f"data: {json.dumps(_sorted_ranking(_load_ranking()))}\n\n"
        try:
            while True:
                deadline = time.time() + 28
                while time.time() < deadline:
                    if q:
                        yield q.pop(0)
                        break
                    time.sleep(0.25)
                else:
                    yield ": heartbeat\n\n"
        finally:
            with _sse_lock:
                if q in _sse_clients:
                    _sse_clients.remove(q)
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
