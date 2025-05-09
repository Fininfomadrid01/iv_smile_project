import os
import sys
import requests
import pandas as pd
from bs4 import BeautifulSoup
from lxml import html
import datetime
import streamlit as st
import plotly.graph_objects as go
import mibian
import json

# Para poder importar el paquete 'scraper' si existe un nivel arriba
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from meff_scraper_classes import MiniIbexOpcionesScraper
from meff_scraper_classes import MiniIbexFuturosScraper

# --------------------------------------------------
# Configuración de Streamlit
# --------------------------------------------------
st.set_page_config(page_title="IV Smile", layout="wide")
st.title("Volatilidad Implícita – Smile de Opciones")

# --------------------------------------------------
# Scrape de FUTUROS desde HTML local de debug_meff_page.html
# --------------------------------------------------
def load_debug_futures():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'debug_meff_page.html'))
    if not os.path.exists(path):
        return pd.DataFrame()
    with open(path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    table = soup.find('table', id='Contenido_Contenido_tblFuturos')
    rows = []
    if table:
        for tr in table.select('tbody tr'):
            cols = tr.find_all('td')
            if cols:
                venc = cols[0].get_text(strip=True).replace('\xa0','')
                ant  = cols[-1].get_text(strip=True).replace('\xa0','')
                rows.append({'VENCIMIENTO': venc, 'ANT.': ant})
    return pd.DataFrame(rows)

# Cargar tabla de FUTUROS desde archivo de debug
df_futures_static = load_debug_futures()

# --------------------------------------------------
# Scraping dinámico de MEFF con las clases
# --------------------------------------------------
url_opciones = "https://cyw9gfj3pf.execute-api.us-east-1.amazonaws.com/dev/opciones"
response_opciones = requests.get(url_opciones)
data_opciones = response_opciones.json()
print("Respuesta de opciones:", data_opciones)
st.write("Respuesta de opciones:", data_opciones)

# Opciones
if isinstance(data_opciones, dict) and 'body' in data_opciones:
    opciones_df = pd.DataFrame(json.loads(data_opciones['body']))
elif isinstance(data_opciones, list):
    opciones_df = pd.DataFrame(data_opciones)
else:
    opciones_df = pd.DataFrame()

url_futuros = "https://cyw9gfj3pf.execute-api.us-east-1.amazonaws.com/dev/futuros"
response_futuros = requests.get(url_futuros)
data_futuros = response_futuros.json()
print("Respuesta de futuros:", data_futuros)
st.write("Respuesta de futuros:", data_futuros)

# Futuros
if isinstance(data_futuros, dict) and 'body' in data_futuros:
    futuros_df = pd.DataFrame(json.loads(data_futuros['body']))
elif isinstance(data_futuros, list):
    futuros_df = pd.DataFrame(data_futuros)
else:
    futuros_df = pd.DataFrame()

# Agrupar opciones por fecha y tipo
fechas = sorted(opciones_df['fecha_venc'].unique())
date_options = [d.strftime("%Y-%m-%d") for d in fechas]
calls_iv = {d.strftime("%Y-%m-%d"): opciones_df[(opciones_df['fecha_venc']==d)&(opciones_df['tipo_opcion']=='CALL')][['strike','precio']].reset_index(drop=True) for d in fechas}
puts_iv  = {d.strftime("%Y-%m-%d"): opciones_df[(opciones_df['fecha_venc']==d)&(opciones_df['tipo_opcion']=='PUT')][['strike','precio']].reset_index(drop=True) for d in fechas}

# --------------------------------------------------
# Selector de fecha usando strings
# --------------------------------------------------
selected_str = st.selectbox(
    "Selecciona fecha de expiración",
    date_options
)
selected_date = datetime.datetime.strptime(selected_str, "%Y-%m-%d").date()

# Obtener DataFrames para la fecha seleccionada
df_calls = calls_iv.get(selected_str, pd.DataFrame())
df_puts  = puts_iv.get(selected_str, pd.DataFrame())
df_call_disp = df_calls.copy()
df_put_disp = df_puts.copy()

# Mostrar tabla de FUTUROS estáticos y dinámicos
st.subheader("Datos de FUTUROS estáticos")
st.dataframe(df_futures_static)
st.subheader("Datos de FUTUROS dinámicos")
st.dataframe(futuros_df)

# =========================
# FUNCIONALIDAD DE PRUEBAS: IV SMILE
# =========================
def get_futuro_para_fecha(fecha, df_fut):
    futuros_validos = df_fut[df_fut['fecha_venc'] >= fecha]
    if not futuros_validos.empty:
        return float(futuros_validos.iloc[0]['precio_ultimo'])
    if not df_fut.empty:
        return float(df_fut.iloc[-1]['precio_ultimo'])
    return None

def calcular_iv(row, precio_futuro):
    try:
        S = precio_futuro
        K = row['strike']
        r = 0
        days = max(int((selected_date - datetime.date.today()).days), 1)
        precio = row['precio']
        if precio <= 0 or S <= 0 or K <= 0:
            return None
        if 'tipo_opcion' in row and row['tipo_opcion'] == 'CALL':
            iv = mibian.BS([S, K, r, days], callPrice=precio).impliedVolatility
        else:
            iv = mibian.BS([S, K, r, days], putPrice=precio).impliedVolatility
        return iv if iv and iv > 0 else None
    except Exception:
        return None

precio_fut = get_futuro_para_fecha(selected_date, futuros_df)

# Calcula IV para Calls y Puts
df_calls_iv = df_calls.copy()
df_puts_iv = df_puts.copy()
if not df_calls_iv.empty:
    df_calls_iv['tipo_opcion'] = 'CALL'
    df_calls_iv['iv'] = df_calls_iv.apply(lambda row: calcular_iv(row, precio_fut), axis=1)
if not df_puts_iv.empty:
    df_puts_iv['tipo_opcion'] = 'PUT'
    df_puts_iv['iv'] = df_puts_iv.apply(lambda row: calcular_iv(row, precio_fut), axis=1)

# Mostrar solo las tablas con IV
st.subheader(f"Calls con volatilidad implícita para {selected_date}")
st.dataframe(df_calls_iv)
st.subheader(f"Puts con volatilidad implícita para {selected_date}")
st.dataframe(df_puts_iv)

# Gráfico de IV Smile
st.subheader('Smile de Volatilidad Implícita (IV) vs Strike')
fig_iv = go.Figure()
if not df_calls_iv.empty and 'iv' in df_calls_iv.columns:
    fig_iv.add_trace(go.Scatter(x=df_calls_iv['strike'], y=df_calls_iv['iv'], mode='lines+markers', name='CALL'))
if not df_puts_iv.empty and 'iv' in df_puts_iv.columns:
    fig_iv.add_trace(go.Scatter(x=df_puts_iv['strike'], y=df_puts_iv['iv'], mode='lines+markers', name='PUT'))
fig_iv.update_layout(xaxis_title='Strike', yaxis_title='Volatilidad Implícita (IV, %)', template='plotly_white')
st.plotly_chart(fig_iv, use_container_width=True)