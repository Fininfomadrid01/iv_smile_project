import os
import json
import boto3
from decimal import Decimal
from scraper.meff_scraper_classes import MiniIbexFuturosScraper

print("[DEBUG] Imports realizados correctamente (futuros)")

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    print("=== INICIO LAMBDA FUTUROS ===")
    """
    Lambda que realiza el scraping de futuros con BeautifulSoup
    y almacena los resultados en la tabla DynamoDB indicada en RAW_TABLE_NAME.
    """
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

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Scraping y guardado de futuros completados"}, default=decimal_default)
    } 