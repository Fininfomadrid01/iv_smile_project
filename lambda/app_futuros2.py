import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import boto3
import os
from decimal import Decimal
import math

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

def obtener_futuros_meff():
    url = 'https://www.meff.es/esp/Derivados-Financieros/Ficha/FIEM_MiniIbex_35'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    rows_fut = soup.select('#Contenido_Contenido_tblFuturos tbody tr')
    data_fut = []
    for row in rows_fut:
        cols = row.find_all('td')
        if len(cols) == 14:
            data_fut.append([clean_value(c.text) for c in cols])

    df_fut = pd.DataFrame(data_fut, columns=[
        'Vencimiento', 'Tipo', 'Compra1', 'Compra2', 'Compra3',
        'Venta1', 'Venta2', 'Venta3', 'Último', 'Volumen',
        'Apertura', 'Máximo', 'Mínimo', 'Anterior'
    ])
    df_fut['Vencimiento'] = pd.to_datetime(df_fut['Vencimiento'], format='%d %b. %Y', errors='coerce')
    df_fut['Anterior'] = df_fut['Anterior'].apply(clean_and_convert)
    df_fut['Último'] = df_fut['Último'].apply(clean_and_convert)
    return df_fut

def generar_id(row, scrape_date):
    # ID: {scrape_date}#{vencimiento}#{tipo}
    vencimiento_str = str(row['Vencimiento'])
    return f"{scrape_date}#{vencimiento_str}#{row['Tipo']}"

def safe_decimal(val):
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return Decimal(str(val))

def lambda_handler(event, context):
    df_fut = obtener_futuros_meff()
    scrape_date = datetime.utcnow().strftime('%Y-%m-%d')

    dynamodb = boto3.resource('dynamodb')
    table_name = os.environ.get('RAW_TABLE_NAME', 'futuros-table')
    table = dynamodb.Table(table_name)

    for _, row in df_fut.iterrows():
        if pd.isna(row['Vencimiento']) or pd.isna(row['Tipo']):
            continue  # Filtra datos incompletos
        item = {
            'id': generar_id(row, scrape_date),
            'scrape_date': scrape_date,
            'vencimiento': str(row['Vencimiento']),
            'tipo': row['Tipo'],
            'ultimo': safe_decimal(row['Último']),
            'anterior': safe_decimal(row['Anterior']),
            'volumen': row['Volumen'],
            # Puedes añadir más campos si lo necesitas
        }
        # Elimina claves con valor None
        item = {k: v for k, v in item.items() if v is not None}
        table.put_item(Item=item)
    return {'statusCode': 200, 'body': 'OK'} 