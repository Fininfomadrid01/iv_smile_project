import boto3

TABLAS = [
    ('dev-raw-prices', 'Opciones/Futuros'),
    ('futuros-table', 'Futuros'),
    ('dev-implied-vols', 'IV'),
]
REGION = 'us-east-1'

client = boto3.client('dynamodb', region_name=REGION)

for tabla, desc in TABLAS:
    print(f"\n=== Ejemplos de registros en {desc} ({tabla}) ===")
    resp = client.scan(TableName=tabla, Limit=5)
    for item in resp['Items']:
        out = {k: v for k, v in item.items() if k in ['id', 'date', 'scrape_date', 'type']}
        print(out) 