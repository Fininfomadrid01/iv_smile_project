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
# Sidebar de debug de datos cargados desde DynamoDB
# --------------------------------------------------
st.sidebar.header("Debug: Fechas de IV cargadas")
# Se actualizará tras cargar los datos

# --------------------------------------------------
# Función para cargar datos de IV directamente desde DynamoDB en lugar de CSV
# --------------------------------------------------
def load_csv_iv():
    import boto3
    from boto3.dynamodb.conditions import Key
    # Inicializar cliente DynamoDB
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("dev-implied-vols")

    # Escanear todos los ítems de la tabla
    response = table.scan()
    items = response.get("Items", [])

    # Crear diccionarios para Calls y Puts
    calls_iv = {}
    puts_iv  = {}
    for item in items:
        date = item.get("date")
        type_op = item.get("type")
        strike = float(item.get("strike"))
        iv = float(item.get("iv"))

        if type_op == "calls":
            calls_iv.setdefault(date, []).append({"Strike": strike, "IV": iv})
        elif type_op == "puts":
            puts_iv .setdefault(date, []).append({"Strike": strike, "IV": iv})

    # Convertir listas a DataFrames
    calls_iv = {d: pd.DataFrame(data) for d, data in calls_iv.items()}
    puts_iv  = {d: pd.DataFrame(data) for d, data in puts_iv.items()}
    return calls_iv, puts_iv

# --------------------------------------------------
# Carga de datos
# --------------------------------------------------
calls_iv, puts_iv = load_csv_iv()

# Mostrar en sidebar las fechas disponibles cargadas
st.sidebar.write(sorted(calls_iv.keys()))
# Fechas disponibles (solo las que tienen datos en calls)
fechas = sorted([d for d, df in calls_iv.items() if not df.empty])
if not fechas:
    st.error("No se han encontrado datos de IV en DynamoDB.")
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