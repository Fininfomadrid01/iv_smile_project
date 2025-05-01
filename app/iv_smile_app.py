
import os
import sys

# Hago que Python busque el paquete 'scraper' un nivel arriba (si lo necesitas)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --------------------------------------------------
# Configuración de la página
# --------------------------------------------------
st.set_page_config(page_title="IV Smile", layout="wide")
st.title("Volatilidad Implícita – Smile de Opciones")

# --------------------------------------------------
# Paths
# --------------------------------------------------
BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# --------------------------------------------------
# Sidebar de debug
# --------------------------------------------------
st.sidebar.header("Debug: CSV disponibles")
st.sidebar.write("Carpeta CSV:", OUTPUT_DIR)
if os.path.isdir(OUTPUT_DIR):
    st.sidebar.write(sorted(os.listdir(OUTPUT_DIR)))
else:
    st.sidebar.error("No existe la carpeta 'output' con CSVs.")

# --------------------------------------------------
# Función para cargar y limpiar los CSV
# --------------------------------------------------
def load_csv_iv():
    calls_iv = {}
    puts_iv  = {}
    if not os.path.isdir(OUTPUT_DIR):
        return calls_iv, puts_iv

    for fname in sorted(os.listdir(OUTPUT_DIR)):
        if not fname.endswith(".csv"):
            continue
        path = os.path.join(OUTPUT_DIR, fname)

        # Determinar tipo y fecha
        if fname.startswith("calls_iv_"):
            key   = "calls"
            fecha = fname[len("calls_iv_"):-4].replace("-", "/")
        elif fname.startswith("puts_iv_"):
            key   = "puts"
            fecha = fname[len("puts_iv_"):-4].replace("-", "/")
        else:
            continue

        # Leer CSV europeo: sep=',' miles='.' decimal=','
        df = pd.read_csv(path, sep=",", thousands=".", decimal=",")
        df.columns = df.columns.str.strip()

        # Quitar fila de 'Volumen Total' si existe
        if "Strike" in df.columns:
            mask = df["Strike"].astype(str).str.lower() != "volumen total"
            df   = df[mask]

        # Requerir columnas Strike e IV
        if "Strike" not in df.columns or "IV" not in df.columns:
            continue

        # Convertir a numérico
        df["Strike"] = pd.to_numeric(df["Strike"], errors="coerce")
        df["IV"]     = pd.to_numeric(df["IV"], errors="coerce")

        # Eliminar filas con NaN
        df = df.dropna(subset=["Strike", "IV"]).reset_index(drop=True)

        # Almacenar
        if key == "calls":
            calls_iv[fecha] = df
        else:
            puts_iv[fecha]   = df

    return calls_iv, puts_iv

# --------------------------------------------------
# Carga de datos
# --------------------------------------------------
calls_iv, puts_iv = load_csv_iv()

# Fechas disponibles (solo las que tienen datos en calls)
fechas = sorted([d for d, df in calls_iv.items() if not df.empty])
if not fechas:
    st.error("No se han encontrado datos de IV en los CSV.")
    st.stop()

# --------------------------------------------------
# Selector de fecha
# --------------------------------------------------
selected_date = st.selectbox("Selecciona fecha de expiración", fechas)

# DataFrames para la fecha elegida
df_calls = calls_iv.get(selected_date, pd.DataFrame())
df_puts  = puts_iv .get(selected_date, pd.DataFrame())

# --------------------------------------------------
# Dibujo de IV Smile
# --------------------------------------------------
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df_calls["Strike"], y=df_calls["IV"],
    mode="lines+markers", name="Calls"
))
if not df_puts.empty:
    fig.add_trace(go.Scatter(
        x=df_puts["Strike"], y=df_puts["IV"],
        mode="lines+markers", line=dict(dash="dash"),
        name="Puts"
    ))
fig.update_layout(
    title=f"IV Smile para {selected_date}",
    xaxis_title="Strike",
    yaxis_title="Volatilidad Implícita (%)",
    legend_title="Tipo de Opción",
    width=900, height=600
)
st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# Mostrar tablas
# --------------------------------------------------
st.subheader(f"Datos de Calls para {selected_date}")
st.dataframe(df_calls)

if not df_puts.empty:
    st.subheader(f"Datos de Puts para {selected_date}")
    st.dataframe(df_puts)