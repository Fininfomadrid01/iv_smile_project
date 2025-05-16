# Copia exacta de iv_smile_app.py para comenzar una nueva versión experimental 

import streamlit as st
import pandas as pd
import requests
import json
import re

st.set_page_config(page_title="IV Smile App v2", layout="wide")

st.title("IV Smile App v2")

st.sidebar.header("Carga de datos")

# Espacio para cargar archivos CSV o conectar a base de datos
uploaded_file = st.sidebar.file_uploader("Sube un archivo CSV de opciones/futuros", type=["csv"]) 

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("Archivo cargado correctamente.")
        st.dataframe(df.head())
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
else:
    st.info("Sube un archivo para comenzar el análisis.")

# Espacio para agregar más módulos, tabs, visualizaciones, etc.
st.write("\n---\n")
st.subheader("Aquí irán los módulos de análisis, visualización y estadísticas.")

# Ejemplo de placeholder para futuras funciones
def placeholder():
    st.write("Módulo futuro aquí...")

placeholder() 

# --- Utilidades de normalización flexible ---
def normaliza_columnas(df):
    renames = {}
    for col in df.columns:
        c = col.lower().strip()
        if c in ["tipo", "type_opcion", "tipo_opcion"]:
            renames[col] = "type"
        elif c in ["fecha", "vencimiento", "fecha_venc"]:
            renames[col] = "date"
        elif c in ["strike_price", "precio_ejercicio"]:
            renames[col] = "strike"
        elif c in ["precio", "price"]:
            renames[col] = "price"
        elif c in ["volumen", "volume"]:
            renames[col] = "volume"
        elif c in ["dias_vto", "dias_vencimiento"]:
            renames[col] = "dias_vto"
        elif c in ["scrape_date", "scrape_datetimestamp"]:
            renames[col] = "scrape_date"
        elif c in ["identificador", "id_opcion", "id_futuro"]:
            renames[col] = "id"
    df = df.rename(columns=renames)
    # Elimina columnas duplicadas si existen
    df = df.loc[:,~df.columns.duplicated()]
    return df

def normaliza_tipo(tipo):
    if not isinstance(tipo, str):
        return tipo
    t = tipo.lower().strip()
    if t in ["call", "calls", "c"]:
        return "call"
    if t in ["put", "puts", "p"]:
        return "put"
    return t

def normaliza_fecha(fecha):
    # Devuelve siempre YYYY-MM-DD como string, sin timestamp
    try:
        return pd.to_datetime(fecha).strftime('%Y-%m-%d')
    except Exception:
        return str(fecha)[:10]  # fallback: toma solo los primeros 10 caracteres

# --- Carga automática desde las APIs ---
@st.cache_data(show_spinner=True)
def cargar_df_api(url):
    try:
        r = requests.get(url)
        data = r.json()
        if isinstance(data, dict) and 'body' in data:
            df = pd.DataFrame(json.loads(data['body']))
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"Error al cargar {url}: {e}")
        return pd.DataFrame()

url_opciones = "https://cyw9gfj3pf.execute-api.us-east-1.amazonaws.com/dev/opciones"
url_futuros  = "https://cyw9gfj3pf.execute-api.us-east-1.amazonaws.com/dev/futuros"
url_iv       = "https://cyw9gfj3pf.execute-api.us-east-1.amazonaws.com/dev/iv"

opciones_df = cargar_df_api(url_opciones)
futuros_df  = cargar_df_api(url_futuros)
iv_df       = cargar_df_api(url_iv)

# --- Normalización flexible de columnas y tipos ---
for df_name in ['opciones_df', 'futuros_df', 'iv_df']:
    if df_name in locals():
        df = locals()[df_name]
        if not df.empty:
            df = normaliza_columnas(df)
            for col in ['date', 'scrape_date']:
                if col in df.columns:
                    df[col] = df[col].apply(normaliza_fecha)
            if 'type' in df.columns:
                df['type'] = df['type'].replace({'calls': 'call', 'puts': 'put'}).apply(normaliza_tipo)
            if 'strike' in df.columns:
                df['strike'] = pd.to_numeric(df['strike'], errors='coerce')
            if 'iv' in df.columns:
                df['iv'] = pd.to_numeric(df['iv'], errors='coerce')
            if 'price' in df.columns:
                df['price'] = pd.to_numeric(df['price'], errors='coerce')
            if 'dias_vto' in df.columns:
                df['dias_vto'] = pd.to_numeric(df['dias_vto'], errors='coerce')
            # Actualiza el DataFrame global
            locals()[df_name] = df

# --- Selección de fecha de scraping ---
st.sidebar.header("Filtros")
scrape_date_sel = None
if not iv_df.empty and 'scrape_date' in iv_df.columns:
    scrape_dates = sorted(set([d for d in iv_df['scrape_date'].dropna().unique() if isinstance(d, str)]))
    scrape_date_sel = st.sidebar.selectbox("Selecciona fecha de scraping", scrape_dates)
    # Filtra el DataFrame por scrape_date seleccionado
    iv_df = iv_df[iv_df['scrape_date'] == scrape_date_sel]

# --- Selección de fecha de ejercicio (vencimiento) ---
if not iv_df.empty and 'date' in iv_df.columns:
    fechas_venc = sorted(set([d for d in iv_df['date'].dropna().unique() if isinstance(d, str)]))
    fecha_venc_sel = st.sidebar.selectbox("Selecciona fecha de ejercicio (vencimiento)", fechas_venc)
else:
    fecha_venc_sel = None
    st.warning("No hay datos de IV para mostrar.")

# --- Gráfico IV vs Strike (Skew) ---
st.header("Smile de Volatilidad Implícita (IV) vs Strike")
if fecha_venc_sel and not iv_df.empty:
    df_plot_raw = iv_df[iv_df['date'] == fecha_venc_sel].copy()
    st.write('Datos solo filtrados por fecha:', df_plot_raw)
    if 'iv' in df_plot_raw.columns:
        st.write('IV nulos:', df_plot_raw['iv'].isnull().sum())
        st.write('IV no nulos:', df_plot_raw['iv'].notnull().sum())
    if 'strike' in df_plot_raw.columns:
        st.write('Tipos de strike:', df_plot_raw['strike'].apply(type).value_counts())
        st.write('Ejemplo de strikes:', df_plot_raw['strike'].head(10))
    # Filtra filas problemáticas
    df_plot = df_plot_raw.copy()
    for col in ['strike', 'iv', 'price', 'dias_vto']:
        if col in df_plot.columns:
            df_plot = df_plot[pd.to_numeric(df_plot[col], errors='coerce').notnull()]
    if 'type' in df_plot.columns:
        df_plot = df_plot[~df_plot['type'].isin(['Difer.'])]
    # DEBUG: Mostrar los datos filtrados antes de graficar
    st.write('Datos filtrados para el gráfico:')
    st.write(df_plot)
    if 'iv' in df_plot.columns:
        st.write('IV min/max:', df_plot['iv'].min(), df_plot['iv'].max())
    df_calls = df_plot[df_plot['type'] == 'call'].sort_values('strike').copy()
    df_puts  = df_plot[df_plot['type'] == 'put'].sort_values('strike').copy()
    import plotly.graph_objects as go
    fig = go.Figure()
    if not df_calls.empty:
        fig.add_trace(go.Scatter(x=df_calls['strike'], y=df_calls['iv'], mode='lines+markers', name='CALL', line=dict(color='blue')))
    if not df_puts.empty:
        fig.add_trace(go.Scatter(x=df_puts['strike'], y=df_puts['iv'], mode='lines+markers', name='PUT', line=dict(color='red')))
    if not df_calls.empty or not df_puts.empty:
        fig.update_layout(
            xaxis_title='Strike',
            yaxis_title='Volatilidad Implícita (IV, %)',
            template='plotly_white',
            legend_title_text='Tipo',
            title=f"Smile de IV para vencimiento: {fecha_venc_sel}"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos de CALL ni PUT para graficar el smile de IV.")
    st.subheader("Datos de IV para la fecha seleccionada")
    # Normaliza tipos antes de mostrar
    for col in ['strike', 'iv', 'price', 'dias_vto']:
        if col in df_plot.columns:
            df_plot.loc[:, col] = pd.to_numeric(df_plot[col], errors='coerce')
    for col in ['date', 'scrape_date']:
        if col in df_plot.columns:
            df_plot.loc[:, col] = df_plot[col].astype(str)
    st.dataframe(df_plot[['strike', 'iv', 'type', 'date', 'scrape_date']])
else:
    st.info("No hay datos suficientes para mostrar el gráfico de skew de volatilidad.")

def parsea_id(id_str):
    # Busca fechas en formato YYYY-MM-DD (con o sin timestamp)
    fechas = re.findall(r'\d{4}-\d{2}-\d{2}', str(id_str))
    tipo = None
    strike = None
    # Busca tipo
    if '#call#' in str(id_str):
        tipo = 'call'
    elif '#put#' in str(id_str):
        tipo = 'put'
    elif '#futures' in str(id_str):
        tipo = 'futures'
    # Busca strike (número al final tras #)
    partes = str(id_str).split('#')
    for p in partes[::-1]:
        try:
            strike = str(int(float(p)))
            break
        except:
            continue
    return {
        'scrape_date': fechas[0] if len(fechas) > 0 else '',
        'date': fechas[1] if len(fechas) > 1 else '',
        'type': tipo if tipo else '',
        'strike': strike if strike else ''
    }

for df_name in ['opciones_df', 'futuros_df', 'iv_df']:
    if df_name in locals():
        df = locals()[df_name]
        if not df.empty and 'id' in df.columns:
            parsed = df['id'].apply(parsea_id).apply(pd.Series)
            for col in ['scrape_date', 'date', 'type', 'strike']:
                if col not in df.columns or df[col].isnull().all():
                    df[col] = parsed[col]
            locals()[df_name] = df 

# DEBUG: Mostrar número de filas antes y después de limpiar/normalizar
st.write('--- DEBUG: FILAS ORIGINALES ---')
if 'iv_df' in locals():
    st.write(f"IVs originales: {len(iv_df)}")
if 'opciones_df' in locals():
    st.write(f"Opciones originales: {len(opciones_df)}")
if 'futuros_df' in locals():
    st.write(f"Futuros originales: {len(futuros_df)}")

# ... después de limpieza y normalización ...
st.write('--- DEBUG: FILAS DESPUÉS DE LIMPIEZA ---')
if 'iv_df' in locals():
    st.write(f"IVs después de limpiar: {len(iv_df)}")
    st.write('Combinaciones únicas scrape_date, date, type:')
    st.write(iv_df[['scrape_date', 'date', 'type']].drop_duplicates())
    st.write('Filas con NaT o vacíos en columnas clave:')
    st.write(iv_df[iv_df['date'].isnull() | iv_df['scrape_date'].isnull() | iv_df['type'].isnull()])
if 'opciones_df' in locals():
    st.write(f"Opciones después de limpiar: {len(opciones_df)}")
    st.write('Combinaciones únicas scrape_date, date, type:')
    st.write(opciones_df[['scrape_date', 'date', 'type']].drop_duplicates())
    st.write('Filas con NaT o vacíos en columnas clave:')
    st.write(opciones_df[opciones_df['date'].isnull() | opciones_df['scrape_date'].isnull() | opciones_df['type'].isnull()])
if 'futuros_df' in locals():
    st.write(f"Futuros después de limpiar: {len(futuros_df)}")
    st.write('Combinaciones únicas scrape_date, date, type:')
    st.write(futuros_df[['scrape_date', 'date', 'type']].drop_duplicates() if 'date' in futuros_df.columns and 'type' in futuros_df.columns else futuros_df[['scrape_date']].drop_duplicates())
    st.write('Filas con NaT o vacíos en columnas clave:')
    if 'date' in futuros_df.columns and 'type' in futuros_df.columns:
        st.write(futuros_df[futuros_df['date'].isnull() | futuros_df['scrape_date'].isnull() | futuros_df['type'].isnull()])
    else:
        st.write(futuros_df[futuros_df['scrape_date'].isnull()]) 