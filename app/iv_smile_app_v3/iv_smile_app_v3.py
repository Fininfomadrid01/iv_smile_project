# Copia exacta de iv_smile_app.py para comenzar una nueva versión experimental 

import streamlit as st
import pandas as pd
import requests
import json
import re
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import griddata

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
                # Limpia valores de tipo 'type' antes de convertir
                df['strike'] = df['strike'].apply(lambda x: x if not isinstance(x, type) else None)
                df['strike'] = pd.to_numeric(df['strike'], errors='coerce')
            if 'iv' in df.columns:
                # Limpia valores de tipo 'type' antes de convertir
                df['iv'] = df['iv'].apply(lambda x: x if not isinstance(x, type) else None)
                df['iv'] = pd.to_numeric(df['iv'], errors='coerce')
            if 'price' in df.columns:
                df['price'] = pd.to_numeric(df['price'], errors='coerce')
            if 'dias_vto' in df.columns:
                df['dias_vto'] = pd.to_numeric(df['dias_vto'], errors='coerce')
            # Actualiza el DataFrame global
            locals()[df_name] = df

# --- Tabs para separar visualizaciones ---
tab1, tab2, tab3 = st.tabs(["Smile de IV", "Comparador de Skews", "Superficie de Volatilidad 3D"])

# --- Smile de IV (un scrape date) ---
with tab1:
    st.header("Smile de Volatilidad Implícita (IV) vs Strike")
    # Solo fechas y vencimientos con IVs no nulos
    scrape_dates = sorted(set(iv_df[iv_df['iv'].notnull()]['scrape_date'].dropna().unique())) if not iv_df.empty and 'scrape_date' in iv_df.columns else []
    fechas_venc = sorted(set(iv_df[iv_df['iv'].notnull()]['date'].dropna().unique())) if not iv_df.empty and 'date' in iv_df.columns else []
    min_date = "2025-05-15"
    scrape_dates = [d for d in scrape_dates if d >= min_date]
    default_date = "2025-05-16"
    index_smile = scrape_dates.index(default_date) if default_date in scrape_dates else 0
    scrape_date_sel = st.sidebar.selectbox("[Smile] Selecciona fecha de scraping", scrape_dates, key="smile_scrape", index=index_smile)
    fecha_venc_sel = st.sidebar.selectbox("[Smile] Selecciona fecha de ejercicio (vencimiento)", fechas_venc, key="smile_venc")
    if fecha_venc_sel and scrape_date_sel and not iv_df.empty:
        df_plot_raw = iv_df[(iv_df['scrape_date'] == scrape_date_sel) & (iv_df['date'] == fecha_venc_sel)].copy()
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
        # Mostrar solo las columnas que existen
        cols_plot = [c for c in ['strike', 'iv', 'type', 'date', 'scrape_date', 'dias_vto'] if c in df_plot.columns]
        st.dataframe(df_plot[cols_plot])
    else:
        st.info("No hay datos suficientes para mostrar el gráfico de skew de volatilidad.")

# --- Comparador de Skews (dos scrape dates) ---
with tab2:
    st.header("Comparador de Skews: IV vs Strike para dos fechas de scrape")
    # Solo fechas y vencimientos con IVs no nulos
    scrape_dates = sorted(set(iv_df[iv_df['iv'].notnull()]['scrape_date'].dropna().unique())) if not iv_df.empty and 'scrape_date' in iv_df.columns else []
    fechas_venc = sorted(set(iv_df[iv_df['iv'].notnull()]['date'].dropna().unique())) if not iv_df.empty and 'date' in iv_df.columns else []
    min_date = "2025-05-15"
    scrape_dates = [d for d in scrape_dates if d >= min_date]
    default_date = "2025-05-16"
    index_comp1 = scrape_dates.index(default_date) if default_date in scrape_dates else 0
    scrape_date_1 = st.sidebar.selectbox("[Comparador] Selecciona primera fecha de scraping", scrape_dates, key="comp_scrape1", index=index_comp1)
    scrape_date_2 = st.sidebar.selectbox("[Comparador] Selecciona segunda fecha de scraping", scrape_dates, key="comp_scrape2")
    fecha_venc_sel_comp = st.sidebar.selectbox("[Comparador] Selecciona fecha de ejercicio (vencimiento)", fechas_venc, key="comp_venc")
    if scrape_date_1 and scrape_date_2 and fecha_venc_sel_comp and not iv_df.empty:
        df1 = iv_df[(iv_df['scrape_date'] == scrape_date_1) & (iv_df['date'] == fecha_venc_sel_comp)].copy()
        df2 = iv_df[(iv_df['scrape_date'] == scrape_date_2) & (iv_df['date'] == fecha_venc_sel_comp)].copy()
        # Agrupa y promedia si hay duplicados por strike y tipo
        if not df1.empty:
            df1 = df1.groupby(['strike', 'type'], as_index=False)['iv'].mean()
        if not df2.empty:
            df2 = df2.groupby(['strike', 'type'], as_index=False)['iv'].mean()
        fig = go.Figure()
        if not df1.empty:
            fig.add_trace(go.Scatter(
                x=df1[df1['type'] == 'call']['strike'], y=df1[df1['type'] == 'call']['iv'],
                mode='lines+markers', name=f'CALL {scrape_date_1}', line=dict(color='blue', dash='solid')))
            fig.add_trace(go.Scatter(
                x=df1[df1['type'] == 'put']['strike'], y=df1[df1['type'] == 'put']['iv'],
                mode='lines+markers', name=f'PUT {scrape_date_1}', line=dict(color='red', dash='solid')))
        if not df2.empty:
            fig.add_trace(go.Scatter(
                x=df2[df2['type'] == 'call']['strike'], y=df2[df2['type'] == 'call']['iv'],
                mode='lines+markers', name=f'CALL {scrape_date_2}', line=dict(color='blue', dash='dash')))
            fig.add_trace(go.Scatter(
                x=df2[df2['type'] == 'put']['strike'], y=df2[df2['type'] == 'put']['iv'],
                mode='lines+markers', name=f'PUT {scrape_date_2}', line=dict(color='red', dash='dash')))
        fig.update_layout(
            xaxis_title='Strike',
            yaxis_title='Volatilidad Implícita (IV, %)',
            template='plotly_white',
            legend_title_text='Tipo y Fecha',
            title=f"Comparación de Skews para vencimiento: {fecha_venc_sel_comp}"
        )
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("Datos de IV para ambas fechas seleccionadas")
        st.write("Primera fecha:")
        cols1 = [c for c in ['strike', 'iv', 'type', 'date', 'scrape_date', 'dias_vto'] if c in df1.columns]
        st.dataframe(df1[cols1])
        st.write("Segunda fecha:")
        cols2 = [c for c in ['strike', 'iv', 'type', 'date', 'scrape_date', 'dias_vto'] if c in df2.columns]
        st.dataframe(df2[cols2])
    else:
        st.info("Selecciona dos fechas de scrape y un vencimiento para comparar los skews.")

with tab3:
    st.header("Superficie de Volatilidad Implícita 3D")
    # Filtros para tipo y fecha
    tipos_disponibles = sorted(iv_df['type'].dropna().unique()) if not iv_df.empty and 'type' in iv_df.columns else []
    tipo_sel = st.sidebar.selectbox("[Superficie] Tipo de opción", tipos_disponibles, key="surf_tipo")
    scrape_dates = sorted(set(iv_df['scrape_date'].dropna().unique())) if not iv_df.empty else []
    min_date = "2025-05-15"
    scrape_dates = [d for d in scrape_dates if d >= min_date]
    default_date = "2025-05-16"
    index_surf = scrape_dates.index(default_date) if default_date in scrape_dates else 0
    scrape_date_sel = st.sidebar.selectbox("[Superficie] Selecciona fecha de scraping", scrape_dates, key="surf_scrape", index=index_surf)
    interp = st.sidebar.checkbox("Interpolar superficie (más suave)", value=True, key="surf_interp")
    if scrape_date_sel and tipo_sel and not iv_df.empty:
        df_surf = iv_df[(iv_df['scrape_date'] == scrape_date_sel) & (iv_df['type'] == tipo_sel)].copy()
        # Asegúrate de tener 'strike', 'dias_vto', 'iv' como numéricos
        for col in ['strike', 'iv']:
            if col in df_surf.columns:
                df_surf[col] = pd.to_numeric(df_surf[col], errors='coerce')
        # Si no existe 'dias_vto', calcúlalo
        if 'dias_vto' not in df_surf.columns and 'date' in df_surf.columns and 'scrape_date' in df_surf.columns:
            try:
                df_surf['dias_vto'] = (pd.to_datetime(df_surf['date']) - pd.to_datetime(df_surf['scrape_date'])).dt.days
            except Exception:
                df_surf['dias_vto'] = np.nan
        else:
            df_surf['dias_vto'] = pd.to_numeric(df_surf['dias_vto'], errors='coerce')
        # Elimina filas con nulos
        df_surf = df_surf.dropna(subset=['strike', 'dias_vto', 'iv'])
        if interp and not df_surf.empty:
            # Interpolación
            strikes = np.linspace(df_surf['strike'].min(), df_surf['strike'].max(), 40)
            dias = np.linspace(df_surf['dias_vto'].min(), df_surf['dias_vto'].max(), 40)
            X, Y = np.meshgrid(dias, strikes)
            points = df_surf[['dias_vto', 'strike']].values
            values = df_surf['iv'].values
            Z = griddata(points, values, (X, Y), method='cubic')
            fig = go.Figure(data=[go.Surface(z=Z, x=X, y=Y, colorscale='Viridis')])
            fig.update_layout(
                title=f"Superficie de Volatilidad Interpolada ({tipo_sel.upper()}) - {scrape_date_sel}",
                scene=dict(
                    xaxis_title='Días hasta vencimiento',
                    yaxis_title='Strike',
                    zaxis_title='IV'
                ),
                autosize=True,
                margin=dict(l=65, r=50, b=65, t=90)
            )
            st.plotly_chart(fig, use_container_width=True)
        elif not df_surf.empty:
            # Superficie original (sin interpolar)
            surf_pivot = df_surf.pivot_table(index='strike', columns='dias_vto', values='iv')
            X, Y = np.meshgrid(surf_pivot.columns, surf_pivot.index)
            Z = surf_pivot.values
            fig = go.Figure(data=[go.Surface(z=Z, x=X, y=Y, colorscale='Viridis')])
            fig.update_layout(
                title=f"Superficie de Volatilidad ({tipo_sel.upper()}) - {scrape_date_sel}",
                scene=dict(
                    xaxis_title='Días hasta vencimiento',
                    yaxis_title='Strike',
                    zaxis_title='IV'
                ),
                autosize=True,
                margin=dict(l=65, r=50, b=65, t=90)
            )
            st.plotly_chart(fig, use_container_width=True)
        # Mostrar solo las columnas que existen
        cols_surf = [c for c in ['strike', 'dias_vto', 'iv', 'date', 'scrape_date', 'type'] if c in df_surf.columns]
        st.dataframe(df_surf[cols_surf])
    else:
        st.info("Selecciona una fecha y tipo para ver la superficie de volatilidad.")

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