import os
import json
import boto3
from decimal import Decimal
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq

# Cliente DynamoDB
futuros_table = boto3.resource('dynamodb').Table('futuros-table')  # Buscar futuros solo por fecha
db_iv_table = boto3.resource('dynamodb').Table(os.environ['IV_TABLE_NAME'])

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

def lambda_handler(event, context):
    """
    Lambda que procesa eventos de RawPrices (DynamoDB Stream), calcula la IV y la almacena en ImpliedVols.
    """
    for record in event.get('Records', []):
        if record['eventName'] not in ['INSERT', 'MODIFY']:
            continue

        new_img = record['dynamodb']['NewImage']
        date = new_img['date']['S']  # Asegúrate de que el formato sea igual al de futuros-table
        type_op = new_img['type']['S']

        # Comprobación de campos obligatorios
        if 'strike' not in new_img or 'price' not in new_img:
            print(f"Registro ignorado por falta de campos: {new_img}")
            continue
        strike = float(new_img['strike']['N'])
        last_price = float(new_img['price']['N'])

        if type_op not in ['calls', 'puts']:
            continue

        # Buscar el futuro solo por fecha
        future_id = f"{date}#futures"
        fut_item = futuros_table.get_item(Key={'id': future_id}).get('Item')
        if not fut_item:
            print(f"No se encontró futuro para {date}")
            continue
        future_price = float(fut_item['last_price'])

        # Calcular IV con Black-Scholes y Scipy
        T = 30/365  # O ajusta con el valor real de días a vencimiento
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

        # Guardar IV en DynamoDB
        item = {
            'id': f"{date}#{type_op}#{strike}",
            'date': date,
            'type': type_op,
            'strike': Decimal(str(strike)),
            'iv': Decimal(str(iv))
        }
        db_iv_table.put_item(Item=item)

    return {'statusCode': 200, 'body': json.dumps({'message': 'IV calculada y guardada'})} 