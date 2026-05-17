from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import csv
import os
from datetime import datetime

app = Flask(__name__)
# Lee SECRET_KEY desde variable de entorno (configúrala en Railway → Variables)
# Si no existe, usa el valor por defecto (funciona pero menos seguro)
app.secret_key = os.environ.get("SECRET_KEY", "rover_asme_2025_secret_key_xyz!")

# ── Credenciales de los 8 grupos ──────────────────────────────────────────────
GROUPS = {
    "admin": {"password": "Proyecto4", "name": "Admin"},
    "grupo1": {"password": "rover01_202610", "name": "grupo1"},
    "grupo2": {"password": "rover02_202610", "name": "grupo2"},
    "grupo3": {"password": "rover03_202610", "name": "grupo3"},
    "grupo4": {"password": "rover04_202610", "name": "grupo4"},
    "grupo5": {"password": "rover05_202610", "name": "grupo5"},
    "grupo6": {"password": "rover06_202610", "name": "grupo6"},
    "grupo7": {"password": "rover07_202610", "name": "grupo7"},
    "grupo8": {"password": "rover08_202610", "name": "grupo8"},
}

# ── Ruta de datos: usa /tmp que SIEMPRE existe en Railway ─────────────────────
# Para persistencia real, agrega un Volume en Railway y apunta a /app/data
DATA_DIR = os.environ.get("DATA_DIR", "/tmp")
DATA_FILE = os.path.join(DATA_DIR, "resultados.csv")

D_TOTAL = 30.48 ** 3  # cm³

# ── Crear CSV si no existe ─────────────────────────────────────────────────────
def init_csv():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except PermissionError:
        pass  # /tmp ya existe, otros paths pueden fallar en Railway

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "Grupo",
                "Design_Score", "Grams", "Pieces",
                "Total_Parts", "Exceptions", "AM_Parts",
                "Width_cm", "Length_cm", "Height_cm", "Volume_cm3",
                "Base_Score", "AM_Ratio_pct", "Final_Score",
                "Dimension_Penalty"
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
        delta_dim    = dimension - D_TOTAL
        design_used  = design * (D_TOTAL / (D_TOTAL + delta_dim))
        penalty_applied = True

    base_score  = design_used + grams + (pieces * 1000)
    am_ratio    = am_parts / effective_parts
    final_score = am_ratio * base_score

    result = {
        "design_used":      round(design_used, 2),
        "grams_pts":        grams,
        "pieces_pts":       pieces * 1000,
        "base_score":       round(base_score, 2),
        "am_parts":         am_parts,
        "effective_parts":  effective_parts,
        "am_ratio_pct":     round(am_ratio * 100, 1),
        "final_score":      round(final_score, 2),
        "dimension":        round(dimension, 2),
        "d_total":          round(D_TOTAL, 2),
        "penalty_applied":  penalty_applied,
    }
    return result, None

# ── Rutas ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "group" in session:
        return redirect(url_for("calculator"))
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():

    # ── Limpiar username ─────────────────────────────────────
    username = (
        request.form.get("username", "")
        .strip()
        .lower()
        .replace(" ", "")
    )

    # ── Limpiar password ─────────────────────────────────────
    password = request.form.get("password", "").strip()

    # ── Debug Railway Logs ───────────────────────────────────
    print("========== LOGIN DEBUG ==========")
    print("USERNAME RECIBIDO:", username)
    print("PASSWORD RECIBIDO:", password)

    # ── Buscar grupo ─────────────────────────────────────────
    group = GROUPS.get(username)

    print("GROUP ENCONTRADO:", group)

    # ── Validación ───────────────────────────────────────────
    if group and group["password"] == password:

        session["group"] = username
        session["group_name"] = group["name"]

        print("LOGIN EXITOSO")

        return redirect(url_for("calculator"))

    print("LOGIN FALLIDO")

    return render_template(
        "login.html",
        error="Usuario o contraseña incorrectos"
    )

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

    # Guardar en CSV
    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            session["group_name"],
            data["design"], data["grams"], data["pieces"],
            data["total_parts"], data["exceptions"], data["am_parts"],
            data["width"], data["length"], data["height"],
            result["dimension"],
            result["base_score"], result["am_ratio_pct"], result["final_score"],
            result["penalty_applied"]
        ])

    return jsonify(result)
    
@app.route("/download_csv")
def download_csv():
    return send_file(DATA_FILE, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
