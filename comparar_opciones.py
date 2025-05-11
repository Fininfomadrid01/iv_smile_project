import boto3
import requests

# Configuración
dynamo_table = 'dev-raw-prices'
region = 'us-east-1'
api_url = 'https://cyw9gfj3pf.execute-api.us-east-1.amazonaws.com/dev/opciones'

# 1. Consulta DynamoDB (todas las opciones)
client = boto3.client('dynamodb', region_name=region)
resp = client.scan(
    TableName=dynamo_table,
    FilterExpression='#t = :call or #t = :put or #t = :calls or #t = :puts',
    ExpressionAttributeNames={'#t': 'type'},
    ExpressionAttributeValues={
        ':call': {'S': 'call'},
        ':put': {'S': 'put'},
        ':calls': {'S': 'calls'},
        ':puts': {'S': 'puts'}
    }
)
dynamo_items = resp['Items']
print(f"Total de opciones en DynamoDB: {len(dynamo_items)}")

# 2. Consulta la API (todas las opciones)
response = requests.get(api_url)
api_items = response.json()
print(f"Total de opciones en API: {len(api_items)}")

# 3. Compara y muestra diferencias
def get_id(item):
    # Para DynamoDB: item['id']['S'], para API: item['id'] o item.get('id')
    if isinstance(item['id'], dict):
        return item['id'].get('S') or item['id'].get('s')
    return item['id']

dynamo_ids = set(get_id(item) for item in dynamo_items)
api_ids = set(get_id(item) for item in api_items)

solo_en_dynamo = dynamo_ids - api_ids
solo_en_api = api_ids - dynamo_ids

print(f"En DynamoDB pero NO en API: {len(solo_en_dynamo)}")
print(f"En API pero NO en DynamoDB: {len(solo_en_api)}")

if solo_en_dynamo:
    print("Ejemplos solo en DynamoDB:", list(solo_en_dynamo)[:5])
if solo_en_api:
    print("Ejemplos solo en API:", list(solo_en_api)[:5]) 