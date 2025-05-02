import os
import json
import boto3
from decimal import Decimal
from scraper.scrape_all_dates_full import scrape_all_dates_full

def lambda_handler(event, context):
    """
    Lambda que realiza el scraping de todas las fechas con scrape_all_dates_full
    y almacena los resultados en la tabla DynamoDB indicada en RAW_TABLE_NAME.
    """
    # Ejecutar scraping completo
    futures, calls, puts = scrape_all_dates_full()

    # Conexión a DynamoDB
    dynamodb = boto3.resource('dynamodb')
    raw_table = dynamodb.Table(os.environ['RAW_TABLE_NAME'])

    # Inserción en batch
    with raw_table.batch_writer() as batch:
        # Futuros
        for fecha, df in futures.items():
            for _, row in df.iterrows():
                item = {
                    'id': f"{fecha}#futures#{row['Strike']}",
                    'date': fecha,
                    'type': 'futures',
                    'strike': Decimal(str(row['Strike'])),
                    'last_price': Decimal(str(row.get('Último', 0)))
                }
                batch.put_item(Item=item)
        # Calls
        for fecha, df in calls.items():
            for _, row in df.iterrows():
                item = {
                    'id': f"{fecha}#calls#{row['Strike']}",
                    'date': fecha,
                    'type': 'calls',
                    'strike': Decimal(str(row['Strike'])),
                    'last_price': Decimal(str(row.get('Último', 0)))
                }
                batch.put_item(Item=item)
        # Puts
        for fecha, df in puts.items():
            for _, row in df.iterrows():
                item = {
                    'id': f"{fecha}#puts#{row['Strike']}",
                    'date': fecha,
                    'type': 'puts',
                    'strike': Decimal(str(row['Strike'])),
                    'last_price': Decimal(str(row.get('Último', 0)))
                }
                batch.put_item(Item=item)

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Datos raw guardados en DynamoDB', 'count': len(futures) + len(calls) + len(puts)})
    } 