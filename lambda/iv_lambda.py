import os
import json
import boto3
from decimal import Decimal
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
from datetime import datetime, timedelta

# Cliente DynamoDB
futuros_table = boto3.resource('dynamodb').Table('futuros-table')  # Buscar futuros solo por fecha
db_iv_table = boto3.resource('dynamodb').Table(os.environ['IV_TABLE_NAME'])
raw_table = boto3.resource('dynamodb').Table(os.environ['RAW_TABLE_NAME'])

def black_scholes_call(S, K, T, r, sigma):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

def black_scholes_put(S, K, T, r, sigma):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

def implied_volatility(option_price, S, K, T, r, tipo='call'):
    def objective(sigma):
        if tipo == 'call':
            return black_scholes_call(S, K, T, r, sigma) - option_price
        else:
            return black_scholes_put(S, K, T, r, sigma) - option_price
    try:
        return brentq(objective, 1e-6, 5)
    except Exception:
        return None

def procesar_opciones_por_fechas(fechas):
    resultados = []
    for fecha in fechas:
        # Buscar todas las opciones de esa fecha
        response = raw_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('date').eq(fecha) &
                            boto3.dynamodb.conditions.Attr('type').is_in(['calls', 'puts', 'call', 'put'])
        )
        opciones = response['Items']
        print(f"Procesando {len(opciones)} opciones para la fecha {fecha}")
        for opcion in opciones:
            type_op = opcion['type']
            strike = float(opcion['strike']) if isinstance(opcion['strike'], (int, float, Decimal)) else float(opcion['strike'])
            last_price = float(opcion['price']) if isinstance(opcion['price'], (int, float, Decimal)) else float(opcion['price'])
            # Buscar el futuro correspondiente
            future_id = f"{fecha}#futures"
            fut_item = futuros_table.get_item(Key={'id': future_id}).get('Item')
            if not fut_item:
                print(f"No se encontró futuro para {fecha}")
                continue
            future_price = float(fut_item['last_price'])
            T = 30/365  # O ajusta con el valor real de días a vencimiento
            r = 0
            tipo = 'call' if type_op in ['calls', 'call'] else 'put'
            iv = implied_volatility(
                option_price=last_price,
                S=future_price,
                K=strike,
                T=T,
                r=r,
                tipo=tipo
            )
            if iv is not None:
                iv = round(iv, 4)
            else:
                print(f"No se pudo calcular IV para {fecha}, strike {strike}")
                continue
            item = {
                'id': f"{fecha}#{type_op}#{strike}",
                'date': fecha,
                'type': type_op,
                'strike': Decimal(str(strike)),
                'iv': Decimal(str(iv)),
                'scrape_date': datetime.utcnow().strftime('%Y-%m-%d')
            }
            db_iv_table.put_item(Item=item)
            print(f"IV calculada y guardada: {item}")
            resultados.append(item)
    return resultados

def lambda_handler(event, context):
    print("=== INICIO LAMBDA IV ===")
    print("EVENTO RECIBIDO:", json.dumps(event))
    # Si viene de stream, procesar como antes
    if 'Records' in event:
        for record in event.get('Records', []):
            if record['eventName'] not in ['INSERT', 'MODIFY']:
                continue
            new_img = record['dynamodb']['NewImage']
            date = new_img['date']['S']
            type_op = new_img['type']['S']
            if 'strike' not in new_img or 'price' not in new_img:
                print(f"Registro ignorado por falta de campos: {new_img}")
                continue
            strike = float(new_img['strike']['N'])
            last_price = float(new_img['price']['N'])
            if type_op not in ['calls', 'puts']:
                continue
            future_id = f"{date}#futures"
            fut_item = futuros_table.get_item(Key={'id': future_id}).get('Item')
            if not fut_item:
                print(f"No se encontró futuro para {date}")
                continue
            future_price = float(fut_item['last_price'])
            T = 30/365
            r = 0
            tipo = 'call' if type_op == 'calls' else 'put'
            iv = implied_volatility(
                option_price=last_price,
                S=future_price,
                K=strike,
                T=T,
                r=r,
                tipo=tipo
            )
            if iv is not None:
                iv = round(iv, 4)
            else:
                print(f"No se pudo calcular IV para {date}, strike {strike}")
                continue
            item = {
                'id': f"{date}#{type_op}#{strike}",
                'date': date,
                'type': type_op,
                'strike': Decimal(str(strike)),
                'iv': Decimal(str(iv)),
                'scrape_date': datetime.utcnow().strftime('%Y-%m-%d')
            }
            db_iv_table.put_item(Item=item)
            print(f"IV calculada y guardada: {item}")
        return {'statusCode': 200, 'body': json.dumps({'message': 'IV calculada y guardada (stream)'})}

    # Si se llama manualmente
    fechas = set()
    if 'date' in event:
        fechas.add(event['date'])
    elif 'start_date' in event and 'end_date' in event:
        start = datetime.strptime(event['start_date'], '%Y-%m-%d')
        end = datetime.strptime(event['end_date'], '%Y-%m-%d')
        delta = (end - start).days
        for i in range(delta + 1):
            fechas.add((start + timedelta(days=i)).strftime('%Y-%m-%d'))
    else:
        # Todas las fechas disponibles en la tabla de opciones
        response = raw_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('type').is_in(['calls', 'puts'])
        )
        for item in response['Items']:
            fechas.add(item['date'])
    resultados = procesar_opciones_por_fechas(fechas)
    return {'statusCode': 200, 'body': json.dumps({'message': f'IV calculada para {len(resultados)} opciones', 'resultados': [str(r['id']) for r in resultados]})} 