import os
import json
import boto3
from decimal import Decimal
from scraper.meff_scraper_classes import MiniIbexFuturosScraper, MiniIbexOpcionesScraper

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    print("=== INICIO LAMBDA ===")
    """
    Lambda que realiza el scraping de futuros y opciones con BeautifulSoup
    y almacena los resultados en la tabla DynamoDB indicada en RAW_TABLE_NAME.
    """
    # Scraping de futuros
    print("[DEBUG] Iniciando scraping de futuros...")
    futuros_scraper = MiniIbexFuturosScraper()
    try:
        print("[DEBUG] Llamando a obtener_futuros()...")
        df_futuros = futuros_scraper.obtener_futuros()
        print(f"[DEBUG] DataFrame de futuros obtenido: tipo={type(df_futuros)}, shape={getattr(df_futuros, 'shape', None)}")
        print("[DEBUG] Columnas del DataFrame de futuros:", getattr(df_futuros, 'columns', None))
        print("[DEBUG] Contenido completo del DataFrame de futuros:")
        print(df_futuros)
    except Exception as e:
        print(f"Error extrayendo futuros: {e}")
        df_futuros = None

    # Scraping de opciones
    print("[DEBUG] Iniciando scraping de opciones...")
    opciones_scraper = MiniIbexOpcionesScraper()
    try:
        df_opciones = opciones_scraper.obtener_opciones()
        print(f"Opciones extraídas:\n{df_opciones}")
    except Exception as e:
        print(f"Error extrayendo opciones: {e}")
        df_opciones = None

    # Conexión a DynamoDB
    dynamodb = boto3.resource('dynamodb')
    raw_table = dynamodb.Table(os.environ['RAW_TABLE_NAME'])

    # Guardar futuros
    if df_futuros is not None and not df_futuros.empty:
        print(f"[DEBUG] Guardando {len(df_futuros)} futuros en DynamoDB...")
        with raw_table.batch_writer() as batch:
            for _, row in df_futuros.iterrows():
                item = {
                    'id': f"{row['fecha_venc']}#futures",
                    'date': str(row['fecha_venc']),
                    'type': 'futures',
                    'last_price': Decimal(str(row['precio_ultimo']))
                }
                print(f"Guardando futuro: {item}")
                batch.put_item(Item=item)
    else:
        print("[DEBUG] No se guardaron futuros (DataFrame vacío o None)")

    # Guardar opciones
    if df_opciones is not None and not df_opciones.empty:
        with raw_table.batch_writer() as batch:
            for _, row in df_opciones.iterrows():
                item = {
                    'id': f"{row['fecha_venc']}#{row['tipo_opcion'].lower()}#{row['strike']}",
                    'date': str(row['fecha_venc']),
                    'type': row['tipo_opcion'].lower(),
                    'strike': Decimal(str(row['strike'])),
                    'price': Decimal(str(row['precio'])),
                    'dias_vto': int(row['dias_vto'])
                }
                print(f"Guardando opción: {item}")
                batch.put_item(Item=item)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Scraping y guardado completados"}, default=decimal_default)
    }