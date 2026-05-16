# R.O.V.E.R — ASME Arena Challenge

Sistema web de puntaje para el concurso de ROVERS (ASME).

## Credenciales de los 8 grupos

| Usuario  | Contraseña |
|----------|------------|
| grupo1   | rover001   |
| grupo2   | rover002   |
| grupo3   | rover003   |
| grupo4   | rover004   |
| grupo5   | rover005   |
| grupo6   | rover006   |
| grupo7   | rover007   |
| grupo8   | rover008   |

> **Cambia las contraseñas** en `app.py` → diccionario `GROUPS` antes de desplegar.

## Despliegue en Railway

1. **Crea una cuenta** en [railway.app](https://railway.app)
2. **Nuevo proyecto** → "Deploy from GitHub repo" (sube este código a un repo GitHub primero)
   - O usa Railway CLI: `railway init` y `railway up`
3. Railway detecta automáticamente el `Procfile` y `requirements.txt`
4. En **Variables** del proyecto Railway agrega:
   - `SECRET_KEY` = cualquier string aleatorio seguro (reemplaza el valor en app.py)
5. Railway asigna una URL pública automáticamente (ej: `rover-app.railway.app`)

## Datos guardados

Los resultados se guardan en `resultados.csv` con columnas:
- Timestamp, Grupo, Design_Score, Grams, Pieces
- Total_Parts, Exceptions, AM_Parts
- Width_cm, Length_cm, Height_cm, Volume_cm3
- Base_Score, AM_Ratio_pct, Final_Score, Dimension_Penalty

> **Nota Railway**: el filesystem es efímero. Para persistir los datos agrega un **Volume** en Railway (Storage → Add Volume → mount path `/app/data`) y cambia `DATA_FILE` en `app.py` a `/app/data/resultados.csv`.

## Correr localmente

```bash
pip install -r requirements.txt
python app.py
```

Abre `http://localhost:5000`
