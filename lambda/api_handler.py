import os
import json
import boto3
from decimal import Decimal

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION'))
table = dynamodb.Table(os.environ['RAW_TABLE_NAME'])

def lambda_handler(event, context):
    # Obtener el parámetro 'type' de la query string (futures, options o ambos)
    tipo = None
    if event.get('queryStringParameters'):
        tipo = event['queryStringParameters'].get('type')

    if tipo in ('futures', 'options', 'calls', 'puts', 'call', 'put'):
        response = table.scan()
        items = [
            item for item in response['Items']
            if item.get('type') == tipo or item.get('tipo') == tipo
        ]
    else:
        response = table.scan()
        items = response['Items']

    return {
        "statusCode": 200,
        "body": json.dumps(items, default=decimal_default)
    } 