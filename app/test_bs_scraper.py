import pandas as pd
import requests
from bs4 import BeautifulSoup

# URL de la página de MEFF
url = 'https://www.meff.es/esp/Derivados-Financieros/Ficha/FIEM_MiniIbex_35'
# Obtener contenido HTML
response = requests.get(url)
response.raise_for_status()

# Parsear con BeautifulSoup
soup = BeautifulSoup(response.content, 'html.parser')

# Capturar opciones de vencimiento del <select>
options = soup.select('select.form-control option')
vencimientos = {}
for option in options:
    val = option.get('value')
    if val:
        vencimientos[val] = option.text.strip()

# Función para limpiar valores de celda
def clean_value(value):
    if isinstance(value, str):
        # Reemplazar espacios no separables y limpiar
        return value.replace('\xa0', '').strip()
    return value

# Recorrer filas del tbody
rows = soup.select('tbody tr')
data = []
for row in rows:
    data_tipo = row.get('data-tipo')
    if not data_tipo:
        continue
    vencimiento = vencimientos.get(data_tipo)
    cols = row.find_all('td')
    if len(cols) < 2:
        continue
    strike = clean_value(cols[0].get_text())
    anterior = clean_value(cols[-1].get_text())
    data.append({'Strike': strike, 'Anterior': anterior, 'Vencimiento': vencimiento})

# Convertir a DataFrame y mostrar
df_opciones = pd.DataFrame(data)
print(df_opciones) 