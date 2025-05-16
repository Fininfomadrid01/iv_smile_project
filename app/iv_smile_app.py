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
import plotly.express as px
import boto3

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

# Mostrar advertencia si hay pocos datos de opciones
if not opciones_df.empty:
    st.write(f"Opciones disponibles: {len(opciones_df)}")
    if len(opciones_df) < 5:
        st.warning("⚠️ Solo hay unos pocos datos de opciones disponibles para la fecha seleccionada. Esto puede deberse a la falta de liquidez o a la disponibilidad limitada en la web de origen.")

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
# Filtra solo fechas a partir del 2025-05-13 (inclusive)
scrape_dates = [d for d in scrape_dates if d >= '2025-05-13']
scrape_dates = sorted(set(scrape_dates))

if scrape_dates:
    # Selecciona por defecto la fecha 2025-05-14 si está disponible, si no la más reciente
    default_date = '2025-05-14'
    if default_date in scrape_dates:
        default_index = scrape_dates.index(default_date)
    else:
        default_index = len(scrape_dates) - 1
    scrape_date_sel = st.selectbox("Selecciona fecha de scraping (snapshot diario)", scrape_dates, index=default_index)
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
st.header("Datos de FUTUROS estáticos")
st.dataframe(df_futures_static)

# --------------------------------------------------
# Selector de fecha de expiración (opciones scrapeadas) y tablas CALL/PUT
# --------------------------------------------------
# (Ocultado temporalmente a petición del usuario)
# if not opciones_df.empty and 'date' in opciones_df.columns:
#     # Normaliza las fechas de vencimiento a solo fecha (YYYY-MM-DD)
#     opciones_df['date_norm'] = pd.to_datetime(opciones_df['date'], errors='coerce').dt.date.astype(str)
#     fechas_opciones = sorted(opciones_df['date_norm'].unique())
#     selected_exp_str = st.selectbox("Selecciona fecha de expiración (Opciones scrapeadas)", fechas_opciones, key="exp_opciones")
#     # Determinar columnas a mostrar
#     columnas_calls = ['strike', 'price']
#     columnas_puts = ['strike', 'price']
#     if 'volume' in opciones_df.columns:
#         columnas_calls.append('volume')
#         columnas_puts.append('volume')
#     elif 'volumen' in opciones_df.columns:
#         columnas_calls.append('volumen')
#         columnas_puts.append('volumen')
#     df_calls_op = opciones_df[(opciones_df['date_norm'] == selected_exp_str) & (opciones_df['type'] == 'call')][columnas_calls].reset_index(drop=True)
#     df_puts_op  = opciones_df[(opciones_df['date_norm'] == selected_exp_str) & (opciones_df['type'] == 'put')][columnas_puts].reset_index(drop=True)
#     # Eliminar columna 'id' si existe
#     if 'id' in df_calls_op.columns:
#         df_calls_op = df_calls_op.drop(columns=['id'])
#     if 'id' in df_puts_op.columns:
#         df_puts_op = df_puts_op.drop(columns=['id'])
#     st.subheader(f"Opciones CALL (scrapeadas) para {selected_exp_str}")
#     st.dataframe(df_calls_op)
#     st.subheader(f"Opciones PUT (scrapeadas) para {selected_exp_str}")
#     st.dataframe(df_puts_op)

# --------------------------------------------------
# Smile de Volatilidad Implícita (IV) vs Strike
# --------------------------------------------------
st.header("Smile de Volatilidad Implícita (IV) vs Strike")
if not iv_df.empty:
    st.write(f"IVs disponibles: {len(iv_df)}")
    if len(iv_df) < 5:
        st.warning("⚠️ Solo hay unos pocos datos de volatilidad implícita (IV) para la fecha seleccionada. El gráfico puede no ser representativo.")
    if len(iv_df) < 2:
        st.info("No hay suficientes datos para mostrar el gráfico de skew de volatilidad.")
    else:
        # Ya hemos filtrado por scrape_date arriba, así que solo usamos el df filtrado
        df_filtrado = iv_df.copy()
        # Normaliza las fechas de vencimiento a solo fecha (YYYY-MM-DD)
        df_filtrado['date_norm'] = pd.to_datetime(df_filtrado['date'], errors='coerce').dt.date.astype(str)
        fechas_vencimiento = []
        labels_vencimiento = []
        for fecha in sorted(df_filtrado['date_norm'].unique()):
            n_calls = df_filtrado[(df_filtrado['date_norm'] == fecha) & (df_filtrado['type'].isin(['call', 'calls']))]['strike'].nunique()
            n_puts = df_filtrado[(df_filtrado['date_norm'] == fecha) & (df_filtrado['type'].isin(['put', 'puts']))]['strike'].nunique()
            if n_calls > 0 and n_puts > 0:
                fechas_vencimiento.append(fecha)
                labels_vencimiento.append(f"{fecha} (CALL: {n_calls}, PUT: {n_puts})")
        # Ordena por fecha
        fechas_labels = sorted(zip(fechas_vencimiento, labels_vencimiento), key=lambda x: x[0])
        fechas_vencimiento, labels_vencimiento = zip(*fechas_labels) if fechas_labels else ([], [])
        if not fechas_vencimiento:
            st.info("No hay fechas de vencimiento con datos de CALL y PUT para este scrape_date.")
        else:
            # Si solo hay una fecha, la seleccionamos automáticamente
            if len(fechas_vencimiento) == 1:
                fecha_venc_sel = fechas_vencimiento[0]
                st.info(f"Mostrando smile para el único vencimiento disponible: {labels_vencimiento[0]}")
            else:
                # Selecciona por defecto la fecha 2025-05-14 si está disponible, si no la última
                default_date = '2025-05-14'
                if default_date in fechas_vencimiento:
                    default_index = fechas_vencimiento.index(default_date)
                else:
                    default_index = len(fechas_vencimiento) - 1
                fecha_venc_idx = st.selectbox(
                    "Selecciona fecha de vencimiento (IV)",
                    range(len(fechas_vencimiento)),
                    format_func=lambda i: labels_vencimiento[i],
                    key="iv_api_v2",
                    index=default_index
                )
                fecha_venc_sel = fechas_vencimiento[fecha_venc_idx]
            df_calls = df_filtrado[(df_filtrado['date_norm'] == fecha_venc_sel) & (df_filtrado['type'].isin(['call', 'calls']))].sort_values('strike').copy()
            df_puts = df_filtrado[(df_filtrado['date_norm'] == fecha_venc_sel) & (df_filtrado['type'].isin(['put', 'puts']))].sort_values('strike').copy()
            # Normaliza tipos antes de mostrar
            for df in [df_calls, df_puts]:
                if 'strike' in df.columns:
                    df.loc[:, 'strike'] = pd.to_numeric(df['strike'], errors='coerce')
                if 'iv' in df.columns:
                    df.loc[:, 'iv'] = pd.to_numeric(df['iv'], errors='coerce')
                if 'price' in df.columns:
                    df.loc[:, 'price'] = pd.to_numeric(df['price'], errors='coerce')
                if 'dias_vto' in df.columns:
                    df.loc[:, 'dias_vto'] = pd.to_numeric(df['dias_vto'], errors='coerce')
                if 'date' in df.columns:
                    df.loc[:, 'date'] = df['date'].astype(str)
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
            # (Ocultada la tabla de IVs disponibles para la fecha seleccionada)
            # st.subheader("Tabla de IVs disponibles para la fecha seleccionada")
            # columnas = ['strike', 'iv']
            # if 'price' in df_calls.columns:
            #     columnas.append('price')
            # if 'dias_vto' in df_calls.columns:
            #     columnas.append('dias_vto')
            # st.write("CALLs:")
            # st.dataframe(df_calls[columnas])
            # if 'price' in df_puts.columns or 'dias_vto' in df_puts.columns:
            #     columnas_put = ['strike', 'iv']
            #     if 'price' in df_puts.columns:
            #         columnas_put.append('price')
            #     if 'dias_vto' in df_puts.columns:
            #         columnas_put.append('dias_vto')
            # else:
            #     columnas_put = columnas
            # st.write("PUTs:")
            # st.dataframe(df_puts[columnas_put])

# --------------------------------------------------
# Comparativa de Skews Históricos
# --------------------------------------------------
st.header("Comparar skews históricos de volatilidad implícita")
if not iv_df.empty and 'scrape_date' in iv_df.columns:
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

# --------------------------------------------------
# Superficie de Volatilidad Implícita (CALLs y PUTs)
# --------------------------------------------------
st.header("Superficie de Volatilidad Implícita")
if not iv_df.empty and 'scrape_date' in iv_df.columns:
    fechas_scraping = sorted(iv_df['scrape_date'].unique())
    scrape_date_surface = st.selectbox("Selecciona fecha de scraping para la superficie", fechas_scraping, key="surface_scraping")
    for tipo in ['call', 'put']:
        df_surface = iv_df[(iv_df['scrape_date'] == scrape_date_surface) & (iv_df['type'] == tipo)]
        if not df_surface.empty:
            surface_data = df_surface.pivot_table(index='date', columns='strike', values='iv')
            if surface_data.shape[0] >= 2 and surface_data.shape[1] >= 2:
                x = surface_data.columns.values  # strikes
                y = surface_data.index.values    # fechas de vencimiento
                z = surface_data.values          # matriz de IVs
                fig = go.Figure(data=[go.Surface(z=z, x=x, y=y)])
                fig.update_layout(
                    title=f'Superficie de Volatilidad Implícita ({tipo.upper()}) - {scrape_date_surface}',
                    scene=dict(
                        xaxis_title='Strike',
                        yaxis_title='Vencimiento',
                        zaxis_title='IV'
                    )
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No hay suficientes datos para mostrar la superficie de volatilidad implícita ({tipo.upper()}).")

# --------------------------------------------------
# Comparativa de IV Smile por fecha de scraping
# --------------------------------------------------
st.header("Comparativa de IV Smile por fecha de scraping")
if not iv_df.empty and 'scrape_date' in iv_df.columns and 'date' in iv_df.columns:
    # Normaliza las fechas de vencimiento a solo fecha (YYYY-MM-DD)
    iv_df['date_norm'] = pd.to_datetime(iv_df['date'], errors='coerce').dt.date.astype(str)
    fechas_venc_disp = sorted(iv_df['date_norm'].unique())
    fecha_venc_sel = st.selectbox("Selecciona fecha de vencimiento para comparar smiles históricos", fechas_venc_disp, key="smile_hist_venc")
    fechas_scraping = sorted(iv_df[iv_df['date_norm'] == fecha_venc_sel]['scrape_date'].unique())
    fechas_seleccionadas = st.multiselect(
        "Selecciona fechas de scraping para comparar smiles",
        fechas_scraping,
        default=fechas_scraping[-2:] if len(fechas_scraping) >= 2 else fechas_scraping
    )
    fig = go.Figure()
    for scrape_date in fechas_seleccionadas:
        for tipo, color in zip(['call', 'put'], ['blue', 'red']):
            df_plot = iv_df[
                (iv_df['scrape_date'] == scrape_date) &
                (iv_df['date_norm'] == fecha_venc_sel) &
                (iv_df['type'].isin([tipo, tipo + 's']))
            ].sort_values('strike')
            if not df_plot.empty:
                fig.add_trace(go.Scatter(
                    x=df_plot['strike'],
                    y=df_plot['iv'],
                    mode='lines+markers',
                    name=f"{tipo.upper()} - {scrape_date}",
                    line=dict(color=color)
                ))
    fig.update_layout(
        title=f"Comparativa de IV Smile para {fecha_venc_sel}",
        xaxis_title="Strike",
        yaxis_title="Volatilidad Implícita (IV)",
        legend_title="Tipo y Fecha de Scraping"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Identificar combinaciones válidas para graficar smile de IV ---
if not iv_df.empty:
    iv_valid = iv_df[iv_df['iv'].notnull()]
    grouped = iv_valid.groupby(['scrape_date', 'date', 'type']).size().unstack(fill_value=0)
    # Asegúrate de que las columnas 'call' y 'put' existen
    for col in ['call', 'put']:
        if col not in grouped.columns:
            grouped[col] = 0
    valid_combos = grouped[(grouped['call'] > 0) & (grouped['put'] > 0)]
    combos_index = valid_combos.index.tolist()
    combos_labels = [f"Scrape: {scrape} | Vencimiento: {vto}" for scrape, vto in combos_index]
    st.info(f"Combinaciones válidas para graficar smile de IV ({len(combos_labels)}):")
    if combos_labels:
        combo_idx = st.selectbox(
            "Selecciona una combinación scrape_date + vencimiento para ver el smile:",
            range(len(combos_labels)),
            format_func=lambda i: combos_labels[i],
            key="combo_smile_selector"
        )
        selected_scrape, selected_vto = combos_index[combo_idx]
        # Filtra el DataFrame para la combinación seleccionada
        df_filtrado = iv_df[(iv_df['scrape_date'] == selected_scrape) & (iv_df['date'] == selected_vto)]
        # Fechas de vencimiento con al menos un CALL y un PUT, y cuenta de strikes (aquí solo una)
        fecha_venc_sel = selected_vto
        df_calls = df_filtrado[df_filtrado['type'].isin(['call', 'calls'])].sort_values('strike').copy()
        df_puts = df_filtrado[df_filtrado['type'].isin(['put', 'puts'])].sort_values('strike').copy()
        # Normaliza tipos antes de mostrar
        for df in [df_calls, df_puts]:
            if 'strike' in df.columns:
                df.loc[:, 'strike'] = pd.to_numeric(df['strike'], errors='coerce')
            if 'iv' in df.columns:
                df.loc[:, 'iv'] = pd.to_numeric(df['iv'], errors='coerce')
            if 'price' in df.columns:
                df.loc[:, 'price'] = pd.to_numeric(df['price'], errors='coerce')
            if 'dias_vto' in df.columns:
                df.loc[:, 'dias_vto'] = pd.to_numeric(df['dias_vto'], errors='coerce')
            if 'date' in df.columns:
                df.loc[:, 'date'] = df['date'].astype(str)
        fig_iv = go.Figure()
        if not df_calls.empty:
            fig_iv.add_trace(go.Scatter(x=df_calls['strike'], y=df_calls['iv'], mode='lines+markers', name='CALL', line=dict(color='blue')))
        if not df_puts.empty:
            fig_iv.add_trace(go.Scatter(x=df_puts['strike'], y=df_puts['iv'], mode='lines+markers', name='PUT', line=dict(color='red')))
        fig_iv.update_layout(
            xaxis_title='Strike',
            yaxis_title='Volatilidad Implícita (IV, %)',
            template='plotly_white',
            legend_title_text='Tipo',
            title=f"Smile de IV para Scrape: {selected_scrape} | Vencimiento: {selected_vto}"
        )
        st.plotly_chart(fig_iv, use_container_width=True)
        st.subheader("Tabla de IVs disponibles para la combinación seleccionada")
        columnas = ['strike', 'iv']
        if 'price' in df_calls.columns:
            columnas.append('price')
        if 'dias_vto' in df_calls.columns:
            columnas.append('dias_vto')
        st.write("CALLs:")
        st.dataframe(df_calls[columnas])
        if 'price' in df_puts.columns or 'dias_vto' in df_puts.columns:
            columnas_put = ['strike', 'iv']
            if 'price' in df_puts.columns:
                columnas_put.append('price')
            if 'dias_vto' in df_puts.columns:
                columnas_put.append('dias_vto')
        else:
            columnas_put = columnas
        st.write("PUTs:")
        st.dataframe(df_puts[columnas_put])
    else:
        st.warning("No hay combinaciones válidas para graficar smiles de IV.")
else:
    st.warning("No hay datos de IV para analizar combinaciones.")

# Normalizar el campo 'type' al cargar los datos de IV y de opciones
if not iv_df.empty and 'type' in iv_df.columns:
    iv_df['type'] = iv_df['type'].replace({'calls': 'call', 'puts': 'put'})
if not opciones_df.empty and 'type' in opciones_df.columns:
    opciones_df['type'] = opciones_df['type'].replace({'calls': 'call', 'puts': 'put'})

# --- NUEVA PESTAÑA: Comparativa de Skews por dos fechas de scrape ---
st.header("Comparar skews de IV para un mismo vencimiento en dos fechas de scrape")
if not iv_df.empty and 'date_norm' in iv_df.columns and 'scrape_date' in iv_df.columns:
    # Selector de vencimiento (fecha normalizada)
    fechas_venc_disp = sorted(iv_df['date_norm'].unique())
    fecha_venc_sel = st.selectbox("Selecciona fecha de vencimiento para comparar skews", fechas_venc_disp, key="skew2_venc")
    # Fechas de scrape disponibles para ese vencimiento
    fechas_scraping = sorted(iv_df[iv_df['date_norm'] == fecha_venc_sel]['scrape_date'].unique())
    if len(fechas_scraping) < 2:
        st.info("No hay suficientes fechas de scrape para comparar skews históricos en este vencimiento.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            fecha1 = st.selectbox("Selecciona la primera fecha de scrape", fechas_scraping, key="skew2_fecha1")
        with col2:
            fecha2 = st.selectbox("Selecciona la segunda fecha de scrape", [f for f in fechas_scraping if f != fecha1], key="skew2_fecha2")
        # Graficar ambos skews
        fig = go.Figure()
        colores = ['blue', 'red']
        for i, fecha in enumerate([fecha1, fecha2]):
            for tipo, color in zip(['call', 'put'], [colores[i], colores[i]]):
                df_plot = iv_df[
                    (iv_df['scrape_date'] == fecha) &
                    (iv_df['date_norm'] == fecha_venc_sel) &
                    (iv_df['type'].isin([tipo, tipo + 's']))
                ].sort_values('strike')
                if not df_plot.empty:
                    fig.add_trace(go.Scatter(
                        x=df_plot['strike'],
                        y=df_plot['iv'],
                        mode='lines+markers',
                        name=f"{tipo.upper()} - {fecha}",
                        line=dict(color=color, dash='solid' if tipo=='call' else 'dash')
                    ))
        fig.update_layout(
            title=f"Comparativa de Skews de IV para {fecha_venc_sel}",
            xaxis_title="Strike",
            yaxis_title="Volatilidad Implícita (IV)",
            legend_title="Tipo y Fecha de Scrape"
        )
        st.plotly_chart(fig, use_container_width=True)
        # Mostrar tablas de datos
        st.subheader(f"Datos de IV para {fecha_venc_sel} - {fecha1}")
        st.dataframe(iv_df[(iv_df['scrape_date'] == fecha1) & (iv_df['date_norm'] == fecha_venc_sel)][['strike', 'iv', 'type']])
        st.subheader(f"Datos de IV para {fecha_venc_sel} - {fecha2}")
        st.dataframe(iv_df[(iv_df['scrape_date'] == fecha2) & (iv_df['date_norm'] == fecha_venc_sel)][['strike', 'iv', 'type']])
else:
    st.info("No hay datos suficientes para comparar skews en dos fechas.")

# --- Utilidades para flexibilidad de campos y fechas ---
def get_first_valid(obj, keys):
    for k in keys:
        v = obj.get(k)
        if v not in [None, '', 'NaN', '-']:
            return v
    return None

def normaliza_tipo(tipo):
    if not isinstance(tipo, str):
        return tipo
    t = tipo.lower().strip()
    if t in ['call', 'calls', 'c']: return 'call'
    if t in ['put', 'puts', 'p']: return 'put'
    return t

# --- Normalización de nombres de columnas y tipos en los DataFrames cargados ---
def normaliza_columnas(df):
    if 'tipo' in df.columns and 'type' not in df.columns:
        df = df.rename(columns={'tipo': 'type'})
    if 'strike_price' in df.columns and 'strike' not in df.columns:
        df = df.rename(columns={'strike_price': 'strike'})
    if 'fecha' in df.columns and 'date' not in df.columns:
        df = df.rename(columns={'fecha': 'date'})
    if 'vencimiento' in df.columns and 'date' not in df.columns:
        df = df.rename(columns={'vencimiento': 'date'})
    return df

if not opciones_df.empty:
    opciones_df = normaliza_columnas(opciones_df)
    opciones_df = opciones_df.copy()
    opciones_df.loc[:, 'type'] = opciones_df['type'].apply(normaliza_tipo)
    opciones_df.loc[:, 'date_norm'] = pd.to_datetime(opciones_df['date'], errors='coerce').dt.date.astype(str)
    if 'scrape_date' not in opciones_df.columns and 'scrape_datetimestamp' in opciones_df.columns:
        opciones_df.loc[:, 'scrape_date'] = opciones_df['scrape_datetimestamp'].str[:10]

if not iv_df.empty:
    iv_df = normaliza_columnas(iv_df)
    iv_df = iv_df.copy()
    iv_df.loc[:, 'type'] = iv_df['type'].apply(normaliza_tipo)
    iv_df.loc[:, 'date_norm'] = pd.to_datetime(iv_df['date'], errors='coerce').dt.date.astype(str)
    if 'scrape_date' not in iv_df.columns and 'scrape_datetimestamp' in iv_df.columns:
        iv_df.loc[:, 'scrape_date'] = iv_df['scrape_datetimestamp'].str[:10]

# --- Antes de graficar, imprime el DataFrame de IVs y multiplica por 100 si es necesario ---
if not iv_df.empty:
    st.write('Previo al gráfico, muestra los primeros IVs:')
    st.write(iv_df.head(20))
    st.write('Columnas:', iv_df.columns)
    st.write('IV min/max:', iv_df['iv'].min(), iv_df['iv'].max())
    if iv_df['iv'].max() < 1:
        iv_df.loc[:, 'iv'] = iv_df['iv'] * 100

# --- NUEVA SECCIÓN: Resumen estadístico de la base de datos ---
tabs = st.tabs(["Smile IV", "Resumen BD"])

with tabs[1]:
    st.header("Resumen estadístico de la base de datos")
    st.subheader("IVs disponibles")
    if not iv_df.empty:
        st.write(f"Total IVs: {len(iv_df)}")
        st.dataframe(iv_df.describe(include='all'))
        st.write("Fechas de scrapeo:", iv_df['scrape_date'].unique())
        st.write("Vencimientos:", iv_df['date'].unique())
        st.write("Tipos:", iv_df['type'].unique())
    else:
        st.info("No hay IVs en la base de datos.")
    st.subheader("Opciones disponibles")
    if not opciones_df.empty:
        st.write(f"Total opciones: {len(opciones_df)}")
        st.dataframe(opciones_df.describe(include='all'))
        st.write("Fechas de scrapeo:", opciones_df['scrape_date'].unique())
        st.write("Vencimientos:", opciones_df['date'].unique())
        st.write("Tipos:", opciones_df['type'].unique())
    else:
        st.info("No hay opciones en la base de datos.")
    st.subheader("Futuros disponibles")
    if 'futuros_df' in locals() and not futuros_df.empty:
        st.write(f"Total futuros: {len(futuros_df)}")
        st.dataframe(futuros_df.describe(include='all'))
        st.write("Fechas de scrapeo:", futuros_df['scrape_date'].unique())
        st.write("Vencimientos:", futuros_df['date'].unique() if 'date' in futuros_df.columns else futuros_df['fecha_venc'].unique())
    else:
        st.info("No hay futuros en la base de datos.")

# --- Limpieza y normalización de DataFrames ---
def limpia_y_normaliza_df(df, tipo_df):
    df = df.copy()
    # Elimina filas con 'Difer.' en columnas de tipo
    for col in ['tipo', 'type']:
        if col in df.columns:
            df = df[~df[col].isin(['Difer.'])]
    # Normaliza fechas
    for col in ['date', 'vencimiento', 'scrape_date']:
        if col in df.columns:
            df.loc[:, col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
            df = df[df[col].notnull()]
    # Elimina valores None en vencimientos
    for col in ['date', 'vencimiento']:
        if col in df.columns:
            df = df[df[col].notnull() & (df[col] != 'None')]
    return df

# Aplica limpieza a opciones y futuros antes de mostrar
if 'opciones_df' in locals() and not opciones_df.empty:
    opciones_df = limpia_y_normaliza_df(opciones_df, 'opciones')
if 'futuros_df' in locals() and not futuros_df.empty:
    futuros_df = limpia_y_normaliza_df(futuros_df, 'futuros')