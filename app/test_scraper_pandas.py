import requests
import pandas as pd
from lxml import html

MEFF_URL = "https://www.meff.es/esp/Derivados-Financieros/Ficha/FIEM_MiniIbex_35.aspx"

# 1) Descargar la página principal
resp = requests.get(MEFF_URL)
resp.raise_for_status()
page = resp.text
print("Página MEFF descargada correctamente.")

# 2) Parsear tabla de Futuros
try:
    futures_df = pd.read_html(page, attrs={'id': 'Contenido_Contenido_tblFuturos'})[0]
    print("Tabla de Futuros:")
    print(futures_df.head().to_string(index=False))
except Exception as e:
    print(f"Error al parsear tabla de Futuros: {e}")

# 3) Extraer las fechas del select OpStrike
tree = html.fromstring(resp.content)
options = tree.xpath('//select[@id="OpStrike"]/option[@value]')
fechas = [(opt.text.strip(), opt.get('value')) for opt in options]
print("Fechas encontradas:", fechas)

# 4) Para cada fecha, llamar al endpoint AJAX usando los parámetros con mayúsculas y cabeceras
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': MEFF_URL,
    'X-Requested-With': 'XMLHttpRequest'
}
for texto, valor in fechas:
    try:
        ajax_url = "https://www.meff.es/Handler/Options.ashx"
        # El handler .NET distingue mayúsculas: 'Serie' y 'Fecha'
        params = {'Serie': 'FIEM_MiniIbex_35', 'Fecha': valor}
        r2 = requests.get(ajax_url, params=params, headers=headers)
        
        r2.raise_for_status()
        # Si devuelve JSON, manejarlo; si HTML, parsear con read_html
        content_type = r2.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            data = r2.json()
            df_opts = pd.DataFrame(data.get('Items', data.get('items', [])))
        else:
            df_opts = pd.read_html(r2.text, attrs={'id': 'tblOpciones'})[0]
        print(f"Opciones ({texto}): {len(df_opts)} registros")
    except Exception as e:
        print(f"Error en fecha {texto}: {e}") 