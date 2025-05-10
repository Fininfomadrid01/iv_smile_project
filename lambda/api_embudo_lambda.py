import os
import json
import boto3
from decimal import Decimal

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    print("DEBUG EVENT:", json.dumps(event))
    path = event.get('path', '')
    print("DEBUG PATH:", path)
    if '/opciones' in path:
        table = dynamodb.Table(os.environ['RAW_TABLE_NAME'])
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('type').is_in(['call', 'put', 'calls', 'puts'])
        )
        data = response['Items']
    elif '/futuros' in path:
        table = dynamodb.Table(os.environ['FUTUROS_TABLE_NAME'])
        response = table.scan()
        data = response['Items']
    elif '/iv' in path:
        table = dynamodb.Table(os.environ['IV_TABLE_NAME'])
        response = table.scan()
        data = response['Items']
    else:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Endpoint no encontrado"})
        }
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data, default=decimal_default)
    } 