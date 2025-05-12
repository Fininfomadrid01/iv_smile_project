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

if (
    isinstance(data_opciones, dict)
    and 'body' in data_opciones
    and data_opciones.get('statusCode', 200) == 200
):
    opciones_df = pd.DataFrame(json.loads(data_opciones['body']))
elif isinstance(data_opciones, list):
    opciones_df = pd.DataFrame(data_opciones)
else:
    opciones_df = pd.DataFrame()
    st.error(f"Error al obtener opciones: {data_opciones.get('body', data_opciones)}")

# Botón para descargar los datos scrapeados de opciones como CSV
if not opciones_df.empty:
    st.download_button(
        label="Descargar opciones scrapeadas (CSV)",
        data=opciones_df.to_csv(index=False).encode('utf-8'),
        file_name='opciones_scrapeadas.csv',
        mime='text/csv'
    )
    st.download_button(
        label="Descargar opciones scrapeadas (JSON)",
        data=opciones_df.to_json(orient='records', force_ascii=False, indent=2).encode('utf-8'),
        file_name='opciones_scrapeadas.json',
        mime='application/json'
    )

url_futuros = "https://cyw9gfj3pf.execute-api.us-east-1.amazonaws.com/dev/futuros"
response_futuros = requests.get(url_futuros)
data_futuros = response_futuros.json()

# Consulta a la API de IV
url_iv = "https://cyw9gfj3pf.execute-api.us-east-1.amazonaws.com/dev/iv"
response_iv = requests.get(url_iv)
data_iv = response_iv.json()

if (
    isinstance(data_iv, dict)
    and 'body' in data_iv
    and data_iv.get('statusCode', 200) == 200
):
    iv_df = pd.DataFrame(json.loads(data_iv['body']))
elif isinstance(data_iv, list):
    iv_df = pd.DataFrame(data_iv)
else:
    iv_df = pd.DataFrame()
    st.error(f"Error al obtener IV: {data_iv.get('body', data_iv)}")

if (
    isinstance(data_futuros, dict)
    and 'body' in data_futuros
    and data_futuros.get('statusCode', 200) == 200
):
    futuros_df = pd.DataFrame(json.loads(data_futuros['body']))
elif isinstance(data_futuros, list):
    futuros_df = pd.DataFrame(data_futuros)
else:
    futuros_df = pd.DataFrame()
    st.error(f"Error al obtener futuros: {data_futuros.get('body', data_futuros)}")

# Selector de fecha de scraping global
scrape_dates = []
for df in [opciones_df, futuros_df, iv_df]:
    if not df.empty and 'scrape_date' in df.columns:
        scrape_dates.extend(df['scrape_date'].unique())
# Filtra solo strings no vacíos y descarta nulos/NaN
scrape_dates = [d for d in scrape_dates if isinstance(d, str) and d.strip() != ""]
scrape_dates = sorted(set(scrape_dates))

if scrape_dates:
    scrape_date_sel = st.selectbox("Selecciona fecha de scraping (snapshot diario)", scrape_dates)
    if not opciones_df.empty and 'scrape_date' in opciones_df.columns:
        opciones_df = opciones_df[opciones_df['scrape_date'] == scrape_date_sel]
    if not futuros_df.empty and 'scrape_date' in futuros_df.columns:
        futuros_df = futuros_df[futuros_df['scrape_date'] == scrape_date_sel]
    if not iv_df.empty and 'scrape_date' in iv_df.columns:
        iv_df = iv_df[iv_df['scrape_date'] == scrape_date_sel]
else:
    st.info("No hay datos con campo scrape_date para filtrar.")

# --------------------------------------------------
# Mostrar tabla de FUTUROS estáticos
# --------------------------------------------------
st.subheader("Datos de FUTUROS estáticos")
st.dataframe(df_futures_static)

# --------------------------------------------------
# Selector de fecha de expiración (opciones scrapeadas) y tablas CALL/PUT
# --------------------------------------------------
if not opciones_df.empty and 'date' in opciones_df.columns:
    fechas_opciones = sorted(opciones_df['date'].unique())
    selected_exp_str = st.selectbox("Selecciona fecha de expiración (Opciones scrapeadas)", fechas_opciones, key="exp_opciones")
    # Determinar columnas a mostrar
    columnas_calls = ['strike', 'price']
    columnas_puts = ['strike', 'price']
    if 'volume' in opciones_df.columns:
        columnas_calls.append('volume')
        columnas_puts.append('volume')
    elif 'volumen' in opciones_df.columns:
        columnas_calls.append('volumen')
        columnas_puts.append('volumen')
    df_calls_op = opciones_df[(opciones_df['date'] == selected_exp_str) & (opciones_df['type'] == 'call')][columnas_calls].reset_index(drop=True)
    df_puts_op  = opciones_df[(opciones_df['date'] == selected_exp_str) & (opciones_df['type'] == 'put')][columnas_puts].reset_index(drop=True)
    # Eliminar columna 'id' si existe
    if 'id' in df_calls_op.columns:
        df_calls_op = df_calls_op.drop(columns=['id'])
    if 'id' in df_puts_op.columns:
        df_puts_op = df_puts_op.drop(columns=['id'])
    st.subheader(f"Opciones CALL (scrapeadas) para {selected_exp_str}")
    st.dataframe(df_calls_op)
    st.subheader(f"Opciones PUT (scrapeadas) para {selected_exp_str}")
    st.dataframe(df_puts_op)

# --------------------------------------------------
# Selector de fecha de consulta y vencimiento, tablas y gráfico Smile
# --------------------------------------------------
if not iv_df.empty:
    fechas_disponibles = sorted(pd.to_datetime(iv_df['date']).dt.date.unique())
    fecha_default = fechas_disponibles[-1] if fechas_disponibles else datetime.date.today()
    fecha_consulta = st.date_input(
        "Selecciona la fecha de consulta",
        value=fecha_default,
        min_value=min(fechas_disponibles),
        max_value=max(fechas_disponibles)
    )

    # Selector de fecha de vencimiento (todas las fechas únicas de vencimiento en IV)
    fechas_venc_disp = sorted(iv_df['date'].unique())
    fecha_venc_sel = st.selectbox("Selecciona fecha de vencimiento (IV)", fechas_venc_disp, key="iv_api_v2")

    # Tabla de Futuros para la fecha de consulta
    futuros_fecha = futuros_df[futuros_df['date'] == str(fecha_consulta)]
    st.subheader("Futuros para la fecha seleccionada")
    st.dataframe(futuros_fecha)

    # Tablas de CALLs y PUTs para la fecha de vencimiento seleccionada
    df_calls = iv_df[(iv_df['date'] == fecha_venc_sel) & (iv_df['type'] == 'call')].sort_values('strike')
    df_puts = iv_df[(iv_df['date'] == fecha_venc_sel) & (iv_df['type'] == 'put')].sort_values('strike')
    st.subheader(f"CALLs para {fecha_venc_sel}")
    st.dataframe(df_calls)
    st.subheader(f"PUTs para {fecha_venc_sel}")
    st.dataframe(df_puts)

    # Gráfico Smile de IV
    st.subheader('Smile de Volatilidad Implícita (IV) vs Strike')
    fig_iv = go.Figure()
    if not df_calls.empty:
        fig_iv.add_trace(go.Scatter(x=df_calls['strike'], y=df_calls['iv'], mode='lines+markers', name='CALL', line=dict(color='blue')))
    if not df_puts.empty:
        fig_iv.add_trace(go.Scatter(x=df_puts['strike'], y=df_puts['iv'], mode='lines+markers', name='PUT', line=dict(color='red')))
    fig_iv.update_layout(
        xaxis_title='Strike',
        yaxis_title='Volatilidad Implícita (IV, %)',
        template='plotly_white',
        legend_title_text='Tipo'
    )
    st.plotly_chart(fig_iv, use_container_width=True)

    # --------------------------------------------------
    # Superficie de Volatilidad Implícita (CALLs y PUTs)
    # --------------------------------------------------
    for tipo in ['call', 'put']:
        df_surface = iv_df[iv_df['type'] == tipo]
        if not df_surface.empty:
            st.subheader(f"Superficie de Volatilidad Implícita ({tipo.upper()})")
            # Pivot para tener strikes como columnas, fechas como filas
            surface_data = df_surface.pivot_table(index='date', columns='strike', values='iv')
            # Comprobar si hay al menos 2 strikes y 2 fechas
            if surface_data.shape[0] < 2 or surface_data.shape[1] < 2:
                st.info(f"No hay suficientes datos para mostrar la superficie de volatilidad implícita ({tipo.upper()}). Se requieren al menos 2 strikes y 2 fechas de vencimiento.")
            else:
                x = surface_data.columns.values  # strikes
                y = surface_data.index.values    # fechas de vencimiento
                z = surface_data.values          # matriz de IVs
                fig = go.Figure(data=[go.Surface(z=z, x=x, y=y)])
                fig.update_layout(
                    title=f'Superficie de Volatilidad Implícita ({tipo.upper()})',
                    scene=dict(
                        xaxis_title='Strike',
                        yaxis_title='Vencimiento',
                        zaxis_title='IV'
                    )
                )
                st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay datos de IV disponibles para graficar.")

# Menú principal en la barra lateral
menu = st.sidebar.radio(
    "Navegación",
    ("Visualización diaria", "Comparar skews históricos"),
    index=0
)

if menu == "Visualización diaria":
    # ... tu flujo actual de visualización diaria ...
    pass  # Aquí va el código existente
else:
    st.header("Comparar skews históricos de volatilidad implícita")
    # Extrae y ordena las fechas únicas disponibles
    fechas_disponibles = sorted(pd.to_datetime(iv_df['scrape_date']).dt.date.unique())
    if len(fechas_disponibles) >= 2:
        col1, col2 = st.columns(2)
        with col1:
            fecha1 = st.date_input(
                "Selecciona la primera fecha de scraping",
                value=fechas_disponibles[-2],
                min_value=min(fechas_disponibles),
                max_value=max(fechas_disponibles),
                key="fecha1"
            )
        with col2:
            fecha2 = st.date_input(
                "Selecciona la segunda fecha de scraping",
                value=fechas_disponibles[-1],
                min_value=min(fechas_disponibles),
                max_value=max(fechas_disponibles),
                key="fecha2"
            )
        fechas_seleccionadas = [str(fecha1), str(fecha2)]
        iv_df_filtrado = iv_df[iv_df['scrape_date'].isin(fechas_seleccionadas)]
        fig = go.Figure()
        for fecha in fechas_seleccionadas:
            for tipo in ['call', 'put']:
                df_tipo = iv_df_filtrado[(iv_df_filtrado['scrape_date'] == fecha) & (iv_df_filtrado['type'] == tipo)]
                if not df_tipo.empty:
                    fig.add_trace(go.Scatter(
                        x=df_tipo['strike'],
                        y=df_tipo['iv'],
                        mode='lines+markers',
                        name=f"{tipo.upper()} - {fecha}"
                    ))
        fig.update_layout(
            title="Comparativa de Skews de Volatilidad Implícita",
            xaxis_title="Strike",
            yaxis_title="Volatilidad Implícita (IV)",
            legend_title="Tipo y Fecha"
        )
        st.plotly_chart(fig)
    else:
        st.info("No hay suficientes fechas para comparar skews históricos.")