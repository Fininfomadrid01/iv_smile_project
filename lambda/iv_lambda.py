import os
import json
import boto3
from decimal import Decimal
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
from datetime import datetime, timedelta
import decimal

# Cliente DynamoDB
futuros_table = boto3.resource('dynamodb').Table(os.environ['FUTUROS_TABLE_NAME'])
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

def buscar_futuro_mas_cercano(fecha_opcion, futuros_table):
    print("Buscando futuro más cercano para la fecha de la opción:", fecha_opcion)
    response = futuros_table.scan()
    futuros = response['Items']
    print("Futuros encontrados:", futuros)
    if not futuros:
        return None
    from datetime import datetime
    fecha_opcion_dt = datetime.strptime(fecha_opcion, '%Y-%m-%d')
    fechas_futuros = []
    for f in futuros:
        try:
            fechas_futuros.append((f, datetime.strptime(f['date'], '%Y-%m-%d')))
        except Exception as e:
            print(f"Error convirtiendo fecha de futuro: {f.get('date', '')}, error: {e}")
            continue
    if not fechas_futuros:
        return None
    # Encuentra el futuro más cercano en días
    futuro_mas_cercano = min(fechas_futuros, key=lambda x: abs((x[1] - fecha_opcion_dt).days))[0]
    print("Futuro más cercano encontrado:", futuro_mas_cercano)
    return futuro_mas_cercano

def buscar_futuro_flexible(date_opcion, tabla_futuros):
    """
    Busca un futuro cuyo vencimiento coincida con la fecha de la opción,
    aceptando tanto formato 'YYYY-MM-DD' como 'YYYY-MM-DD 00:00:00'.
    Si no encuentra exacto, busca el más cercano.
    """
    response = tabla_futuros.scan()
    futuros = response['Items']
    if not futuros:
        return None
    # Normaliza la fecha de la opción (quita hora si la tiene)
    from datetime import datetime
    try:
        fecha_base = datetime.strptime(str(date_opcion)[:10], '%Y-%m-%d').date()
    except Exception:
        return None
    # Busca coincidencia exacta en 'date' o 'vencimiento'
    for f in futuros:
        for key in ['date', 'vencimiento']:
            v = f.get(key)
            if v:
                try:
                    v_date = datetime.strptime(str(v)[:10], '%Y-%m-%d').date()
                    if v_date == fecha_base:
                        return f
                except Exception:
                    continue
    # Si no hay coincidencia exacta, busca el futuro más cercano
    fechas_futuros = []
    for f in futuros:
        for key in ['date', 'vencimiento']:
            v = f.get(key)
            if v:
                try:
                    v_date = datetime.strptime(str(v)[:10], '%Y-%m-%d').date()
                    fechas_futuros.append((f, v_date))
                except Exception:
                    continue
    if not fechas_futuros:
        return None
    futuro_mas_cercano = min(fechas_futuros, key=lambda x: abs((x[1] - fecha_base).days))[0]
    return futuro_mas_cercano

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
            # Conversión robusta de strike
            strike_raw = str(opcion['strike'])
            try:
                strike = float(strike_raw.replace('.', '').replace(',', '.'))
            except Exception as e:
                print(f"[IV ERROR] Strike inválido: '{strike_raw}' | Error: {e}")
                continue
            type_op = opcion['type']
            last_price = float(opcion['price']) if isinstance(opcion['price'], (int, float, Decimal)) else float(opcion['price'])
            # FILTRO NUEVO: solo procesar precios válidos
            if last_price is None or np.isnan(last_price) or last_price <= 0:
                print(f"[IV WARNING] Strike {strike} con precio inválido ({last_price}), no se calcula IV.")
                continue
            # Buscar el futuro correspondiente
            future_id = f"{fecha}#futures"
            fut_item = futuros_table.get_item(Key={'id': future_id}).get('Item')
            if not fut_item:
                # Buscar el futuro más cercano si no hay coincidencia exacta
                fut_item = buscar_futuro_flexible(fecha, futuros_table)
                if not fut_item:
                    print(f"No se encontró futuro para {fecha} (ni cercano)")
                    continue
            # Obtención flexible del precio del futuro
            S = get_first_valid(fut_item, ['last_price', 'Ant', 'Ant.', 'precio', 'price', 'ultimo'])
            if S is None:
                print(f"[IV ERROR] Futuro sin precio válido: {fut_item}")
                continue
            S = float(S)
            T = 30/365  # O ajusta con el valor real de días a vencimiento
            r = 0
            tipo = 'call' if type_op in ['calls', 'call'] else 'put'
            iv = implied_volatility(
                option_price=last_price,
                S=S,
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
            scrape_date = datetime.utcnow().strftime('%Y-%m-%d')
            item = {
                'id': f"{scrape_date}#{fecha}#{type_op}#{strike}",
                'date': fecha,
                'type': type_op,
                'strike': Decimal(str(strike)),
                'iv': Decimal(str(iv)),
                'scrape_date': scrape_date
            }
            db_iv_table.put_item(Item=item)
            print(f"IV calculada y guardada: {item}")
            resultados.append(item)
    return resultados

def get_first_valid(obj, keys):
    for k in keys:
        v = obj.get(k)
        if v not in [None, '', 'NaN', '-']:
            return v
    return None

def construir_id_flexible(obj):
    scrape_date = get_first_valid(obj, ['scrape_date'])
    vencimiento = get_first_valid(obj, ['date', 'fecha', 'vencimiento'])
    tipo = get_first_valid(obj, ['type', 'tipo'])
    strike = get_first_valid(obj, ['strike', 'strike_price'])
    fecha_venc = str(vencimiento)[:10] if vencimiento else ''
    tipo_norm = str(tipo).lower().rstrip('s') if tipo else ''
    if strike is not None:
        try:
            strike_norm = str(float(str(strike).replace('.', '').replace(',', '.')))
        except Exception:
            strike_norm = str(strike)
        return f"{scrape_date}#{fecha_venc}#{tipo_norm}#{strike_norm}"
    else:
        return f"{scrape_date}#{fecha_venc}#{tipo_norm}"

def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    tabla_opciones = dynamodb.Table(os.environ['RAW_TABLE_NAME'])
    tabla_iv = dynamodb.Table(os.environ['IV_TABLE_NAME'])
    tabla_futuros = dynamodb.Table(os.environ['FUTUROS_TABLE_NAME'])

    # 1. Scan de todas las opciones (con paginación)
    opciones = []
    response = tabla_opciones.scan()
    opciones.extend(response['Items'])
    while 'LastEvaluatedKey' in response:
        response = tabla_opciones.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        opciones.extend(response['Items'])

    # --- DEPURACIÓN: Mostrar todos los scrape_date leídos ---
    print("Valores únicos de scrape_date leídos:", set([op.get('scrape_date') for op in opciones]))
    hoy = datetime.utcnow().strftime('%Y-%m-%d')
    print(f"Filtrando solo opciones con scrape_date = {hoy}")
    opciones_hoy = [op for op in opciones if op.get('scrape_date') == hoy]
    print(f"Total opciones con scrape_date = {hoy}: {len(opciones_hoy)}")

    # Buscar el futuro más próximo al scrape_date (hoy)
    futuro = buscar_futuro_mas_cercano(hoy, tabla_futuros)
    if not futuro:
        print(f"No se encontró futuro para el scrape_date {hoy}")
        return {'statusCode': 200, 'body': json.dumps({'message': f'No se encontró futuro para el scrape_date {hoy}', 'resultados': []})}
    S = get_first_valid(futuro, ['last_price', 'Ant', 'Ant.', 'precio', 'price', 'ultimo'])
    if S is None:
        print(f"[IV ERROR] Futuro sin precio válido: {futuro}")
        return {'statusCode': 200, 'body': json.dumps({'message': f'Futuro sin precio válido para el scrape_date {hoy}', 'resultados': []})}
    S = float(S)

    resultados = []  # Para almacenar los IDs de las IVs calculadas
    ivs_calculadas = []  # Para almacenar los ítems completos de IV
    for opcion in opciones_hoy:
        # Usar nombres flexibles para los campos
        strike = get_first_valid(opcion, ['strike', 'strike_price'])
        price = get_first_valid(opcion, ['Ant', 'Ant.', 'price', 'ultimo', 'last_price'])
        date = get_first_valid(opcion, ['date', 'fecha', 'vencimiento'])
        tipo = get_first_valid(opcion, ['type', 'tipo'])
        scrape_date = get_first_valid(opcion, ['scrape_date'])
        required = {'strike': strike, 'price': price, 'date': date, 'tipo': tipo, 'scrape_date': scrape_date}
        missing = [k for k, v in required.items() if v in [None, '', 'NaN', '-']]
        if missing:
            print(f"[IV WARNING] Opción incompleta (faltan: {missing}), se omite: {opcion}")
            continue
        try:
            strike_f = float(str(strike).replace('.', '').replace(',', '.'))
        except Exception as e:
            print(f"[IV ERROR] Strike inválido: '{strike}' | Error: {e}")
            continue
        try:
            price_f = float(price)
        except Exception as e:
            print(f"[IV ERROR] Precio inválido: '{price}' | Error: {e}")
            continue
        if price_f <= 0 or (isinstance(price_f, float) and np.isnan(price_f)):
            print(f"[IV WARNING] Opción con precio inválido, se omite: {opcion}")
            continue
        # Normaliza tipo
        tipo_norm = str(tipo).lower().rstrip('s')
        # Calcular T real: días entre scrape_date y vencimiento de la opción
        try:
            dt_scrape = datetime.strptime(str(scrape_date)[:10], '%Y-%m-%d')
            dt_vto = datetime.strptime(str(date)[:10], '%Y-%m-%d')
            dias_vto = max((dt_vto - dt_scrape).days, 1)
            T = dias_vto / 365
        except Exception as e:
            print(f"[IV ERROR] Error calculando días a vencimiento: {e}")
            T = 30/365  # fallback
        r = 0
        iv = implied_volatility(
            option_price=price_f,
            S=S,
            K=strike_f,
            T=T,
            r=r,
            tipo=tipo_norm
        )
        iv = round(iv, 4) if iv is not None else None
        item_iv = {
            'id': construir_id_flexible({
                'scrape_date': scrape_date,
                'date': date,
                'tipo': tipo_norm,
                'strike': strike_f
            }),
            'date': date,
            'strike': Decimal(strike_f),
            'type': tipo_norm,
            'iv': Decimal(str(iv)) if iv is not None else None,
            'scrape_date': scrape_date
        }
        # Eliminar campos None para evitar errores con DynamoDB
        item_iv_clean = {k: v for k, v in item_iv.items() if v is not None}
        tabla_iv.put_item(Item=item_iv_clean)
        print(f"IV calculada y guardada: {item_iv_clean}")
        resultados.append(item_iv['id'])
        ivs_calculadas.append(item_iv_clean)  # Añadir el ítem completo
    print(f"Total opciones procesadas para IV: {len(resultados)}")
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'IV calculada para {len(resultados)} opciones',
            'resultados': resultados,
            'ivs': ivs_calculadas
        }, default=decimal_default)
    } 