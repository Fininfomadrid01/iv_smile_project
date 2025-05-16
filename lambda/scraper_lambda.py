import os
import json
import boto3
from decimal import Decimal
from scraper.meff_scraper_classes import MiniIbexFuturosScraper, MiniIbexOpcionesScraper
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup

print("[DEBUG] Imports realizados correctamente")

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def limpiar_texto(texto):
    if isinstance(texto, str):
        return texto.replace('\xa0', '').replace('&nbsp;', '').strip()
    return texto

def convertir_a_float(valor):
    if not valor or valor in ('-', ''):
        return None
    try:
        return float(valor.replace('.', '').replace(',', '.'))
    except Exception:
        return None

def obtener_opciones_meff():
    url = 'https://www.meff.es/esp/Derivados-Financieros/Ficha/FIEM_MiniIbex_35'
    html = requests.get(url).content
    soup = BeautifulSoup(html, 'html.parser')

    # Mapear vencimientos
    venc_dict = {}
    for opt in soup.select('select.form-control option'):
        if opt.get('value'):
            venc_dict[opt['value']] = opt.text.strip()

    # Extraer opciones
    opciones = []
    for fila in soup.select('table#tblOpciones tbody tr[data-tipo]'):
        tipo_raw = fila['data-tipo']
        tipo_opcion = 'call' if 'C' in tipo_raw else 'put'
        vencimiento = venc_dict.get(tipo_raw, None)
        if vencimiento is None and 'OPE' in tipo_raw:
            tipo_raw = tipo_raw.replace('OPE', 'OCE')
            vencimiento = venc_dict.get(tipo_raw, None)
        celdas = fila.find_all('td')
        if not celdas:
            continue
        strike = limpiar_texto(celdas[0].text)
        ant = limpiar_texto(celdas[-1].text)
        opciones.append({
            'fecha_venc': pd.to_datetime(vencimiento, dayfirst=True, errors='coerce'),
            'tipo_opcion': tipo_opcion,
            'strike': convertir_a_float(strike),
            'precio': convertir_a_float(ant)
        })

    df_opciones = pd.DataFrame(opciones)
    hoy = datetime.utcnow().date()
    df_opciones['dias_vto'] = (df_opciones['fecha_venc'] - pd.to_datetime(hoy)).dt.days
    return df_opciones

def lambda_handler(event, context):
    print("=== INICIO LAMBDA ===")
    """
    Lambda que realiza el scraping de futuros y opciones con BeautifulSoup
    y almacena los resultados en la tabla DynamoDB indicada en RAW_TABLE_NAME.
    """
    # Scraping de futuros
    print("[DEBUG] Iniciando scraping de futuros...")
    futuros_scraper = MiniIbexFuturosScraper()
    print("[DEBUG] Antes del try de futuros")
    try:
        print("[DEBUG] Llamando a obtener_futuros()...")
        df_futuros = futuros_scraper.obtener_futuros()
        print(f"[DEBUG] DataFrame de futuros obtenido: tipo={type(df_futuros)}, shape={getattr(df_futuros, 'shape', None)}")
        print("[DEBUG] Columnas del DataFrame de futuros:", getattr(df_futuros, 'columns', None))
        print("[DEBUG] Contenido completo del DataFrame de futuros:")
        print(df_futuros)
    except Exception as e:
        import traceback
        print(f"Error extrayendo futuros: {e}")
        print(traceback.format_exc())
        df_futuros = None

    # Scraping de opciones
    print("[DEBUG] Iniciando scraping de opciones...")
    df_opciones = obtener_opciones_meff()
    print(f"Opciones extraídas:\n{df_opciones}")

    # Conexión a DynamoDB
    dynamodb = boto3.resource('dynamodb')
    raw_table = dynamodb.Table(os.environ['RAW_TABLE_NAME'])

    # Guardar futuros
    if df_futuros is not None and not df_futuros.empty:
        print(f"[DEBUG] Guardando {len(df_futuros)} futuros en DynamoDB...")
        with raw_table.batch_writer() as batch:
            for _, row in df_futuros.iterrows():
                scrape_date = datetime.utcnow().strftime('%Y-%m-%d')
                item = {
                    'id': f"{scrape_date}#{row['fecha_venc']}#futures",
                    'date': str(row['fecha_venc']),
                    'type': 'futures',
                    'last_price': Decimal(str(row['precio_ultimo'])),
                    'scrape_date': scrape_date
                }
                print(f"Guardando futuro: {item}")
                batch.put_item(Item=item)
    else:
        print("[DEBUG] No se guardaron futuros (DataFrame vacío o None)")

    # Guardar opciones
    if df_opciones is not None and not df_opciones.empty:
        with raw_table.batch_writer() as batch:
            for _, row in df_opciones.iterrows():
                # Saltar si el precio es NaN
                if pd.isna(row['precio']):
                    print(f"Saltando opción con precio NaN: {row}")
                    continue
                scrape_date = datetime.utcnow().strftime('%Y-%m-%d')
                item = {
                    'id': f"{scrape_date}#{row['fecha_venc']}#{row['tipo_opcion'].lower()}#{row['strike']}",
                    'date': str(row['fecha_venc']),
                    'type': row['tipo_opcion'].lower(),
                    'strike': Decimal(str(row['strike'])),
                    'price': Decimal(str(row['precio'])),
                    'dias_vto': int(row['dias_vto']),
                    'scrape_date': scrape_date
                }
                print(f"Guardando opción: {item}")
                batch.put_item(Item=item)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Scraping y guardado completados"}, default=decimal_default)
    }