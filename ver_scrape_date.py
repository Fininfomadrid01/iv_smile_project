import boto3

TABLAS = [
    ('dev-raw-prices', 'Opciones/Futuros'),
    ('futuros-table', 'Futuros'),
    ('dev-implied-vols', 'IV'),
]
REGION = 'us-east-1'

client = boto3.client('dynamodb', region_name=REGION)

for tabla, desc in TABLAS:
    print(f"\n=== Registros en {desc} ({tabla}) ===")
    last_evaluated_key = None
    total = 0
    con_scrape_date = 0
    sin_scrape_date = 0
    while True:
        if last_evaluated_key:
            resp = client.scan(TableName=tabla, ExclusiveStartKey=last_evaluated_key)
        else:
            resp = client.scan(TableName=tabla)
        for item in resp['Items']:
            out = {k: v for k, v in item.items() if k in ['id', 'date', 'scrape_date', 'type']}
            print(out)
            total += 1
            if 'scrape_date' in item:
                con_scrape_date += 1
            else:
                sin_scrape_date += 1
        last_evaluated_key = resp.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
    print(f"Total registros: {total}")
    print(f"Con scrape_date: {con_scrape_date}")
    print(f"Sin scrape_date: {sin_scrape_date}") 