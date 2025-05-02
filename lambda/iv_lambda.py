import os
import json
import boto3
from decimal import Decimal
import mibian

# Cliente DynamoDB
dynamodb = boto3.resource('dynamodb')
raw_table = os.environ['RAW_TABLE_NAME']
iv_table = os.environ['IV_TABLE_NAME']


def lambda_handler(event, context):
    """
    Lambda que procesa eventos de RawPrices (DynamoDB Stream), calcula la IV y la almacena en ImpliedVols.
    """
    for record in event.get('Records', []):
        if record['eventName'] not in ['INSERT', 'MODIFY']:
            continue

        new_img = record['dynamodb']['NewImage']
        # Extraer datos raw
        date = new_img['date']['S']
        type_op = new_img['type']['S']
        strike = float(new_img['strike']['N'])
        last_price = float(new_img['last_price']['N'])

        # Solo calls y puts
        if type_op not in ['calls', 'puts']:
            continue

        # Leer precio futuro para la misma fecha
        table = dynamodb.Table(raw_table)
        future_id = f"{date}#futures#{strike}"
        fut_item = table.get_item(Key={'id': future_id}).get('Item')
        if not fut_item:
            print(f"No se encontró futuro para {date} y strike {strike}")
            continue
        future_price = float(fut_item['last_price'])

        # Calcular días hasta expiración: parse fecha dd/mm/YYYY → fecha
        # Suponemos date en formato DD/MM/YYYY
        dd, mm, yyyy = date.split('/')
        expiration = f"{dd}/{mm}/{yyyy}"

        # Calcular IV con mibian
        tasa = 0  # asumimos 0% rate
        iv = mibian.BS([future_price, strike, tasa, expiration], callPrice=last_price).impliedVolatility
        iv = round(iv / 100, 4)

        # Guardar IV en DynamoDB
        iv_tab = dynamodb.Table(iv_table)
        item = {
            'id': f"{date}#{type_op}#{strike}",
            'date': date,
            'type': type_op,
            'strike': Decimal(str(strike)),
            'iv': Decimal(str(iv))
        }
        iv_tab.put_item(Item=item)

    return {'statusCode': 200, 'body': json.dumps({'message': 'IV calculada y guardada'})} 