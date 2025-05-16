import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import boto3
import os
import math
from decimal import Decimal

def clean_value(val):
    if isinstance(val, str):
        val = val.replace('&nbsp;', '').strip()
    return val

def clean_and_convert(val):
    if val in ('-', '', None):
        return None
    val = val.replace('.', '').replace(',', '.')
    try:
        return float(val)
    except ValueError:
        return None

def safe_decimal(val):
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return Decimal(str(val))

def obtener_datos_meff():
    url = 'https://www.meff.es/esp/Derivados-Financieros/Ficha/FIEM_MiniIbex_35'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    options = soup.select('select.form-control option')
    vencimientos = {opt['value']: opt.text.strip() for opt in options}

    rows_opciones = soup.select('table#tblOpciones tbody tr[data-tipo]')
    data_opciones = []

    for row in rows_opciones:
        data_tipo = row['data-tipo']
        type_opt = 'call' if data_tipo[1] == 'C' else 'put'
        vencimiento_str = vencimientos.get(data_tipo, None)
        if vencimiento_str is None:
            data_tipo_clean = data_tipo.replace('OPE', 'OCE') if 'OPE' in data_tipo else data_tipo
            vencimiento_str = vencimientos.get(data_tipo_clean, None)
        cols = row.find_all('td')
        if not cols or len(cols) < 2:
            continue
        strike = clean_value(cols[0].text)
        ant = clean_value(cols[-1].text)
        data_opciones.append([strike, ant, vencimiento_str, type_opt])

    df_opciones = pd.DataFrame(data_opciones, columns=['Strike', 'Anterior', 'Vencimiento', 'Tipo'])
    df_opciones['Vencimiento'] = pd.to_datetime(df_opciones['Vencimiento'], format='%d/%m/%Y', errors='coerce')
    df_opciones['Strike'] = df_opciones['Strike'].apply(clean_and_convert)
    df_opciones['Anterior'] = df_opciones['Anterior'].apply(clean_and_convert)
    return df_opciones

def generar_id(row, scrape_date):
    vencimiento_str = str(row['Vencimiento'])
    return f"{scrape_date}#{vencimiento_str}#{row['Tipo']}#{row['Strike']}"

def lambda_handler(event, context):
    df_opciones = obtener_datos_meff()
    scrape_date = datetime.utcnow().strftime('%Y-%m-%d')

    dynamodb = boto3.resource('dynamodb')
    table_name = os.environ.get('RAW_TABLE_NAME', 'opciones-table')
    table = dynamodb.Table(table_name)

    print("Vencimientos únicos encontrados:", df_opciones['Vencimiento'].unique())
    print("Primeras filas del DataFrame de opciones:")
    print(df_opciones.head(10))

    for _, row in df_opciones.iterrows():
        if pd.isna(row['Vencimiento']) or pd.isna(row['Tipo']) or pd.isna(row['Strike']):
            continue  # Filtra datos incompletos
        item = {
            'id': generar_id(row, scrape_date),
            'scrape_date': scrape_date,
            'vencimiento': str(row['Vencimiento']),
            'tipo': row['Tipo'],
            'strike': safe_decimal(row['Strike']),
            'Ant': safe_decimal(row['Anterior']),
            # Puedes añadir más campos si lo necesitas
        }
        item = {k: v for k, v in item.items() if v is not None}
        print("Guardando opción:", item)
        table.put_item(Item=item)
    print("Total de filas en el DataFrame de opciones:", len(df_opciones))
    return {'statusCode': 200, 'body': 'OK'} 