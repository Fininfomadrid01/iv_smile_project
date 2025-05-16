import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
import numpy as np

class MiniIbexOpcionesScraper:
    """
    Scraper para extraer opciones del Mini IBEX desde la web de MEFF.
    """
    BASE_URL = "https://www.meff.es/esp/Derivados-Financieros/Ficha/FIEM_MiniIbex_35"

    def __init__(self):
        self.session = requests.Session()

    def fetch_html(self):
        resp = self.session.get(self.BASE_URL)
        resp.raise_for_status()
        return resp.text

    def _mapear_vencimientos(self, soup):
        venc_dict = {}
        select = soup.find("select", id="OpStrike")
        if not select:
            return venc_dict
        for opt in select.find_all("option"):
            cod = opt.get("value")
            texto = opt.text.strip()
            try:
                fecha = datetime.datetime.strptime(texto, "%d/%m/%Y").date()
                venc_dict[cod] = fecha
                if cod.startswith("OCE"):
                    venc_dict[cod.replace("OCE", "OPE")] = fecha
            except Exception:
                continue
        return venc_dict

    def obtener_opciones(self):
        html = self.fetch_html()
        soup = BeautifulSoup(html, "html.parser")
        vencimientos = self._mapear_vencimientos(soup)
        tabla = soup.find("table", id="tblOpciones")
        if not tabla:
            raise RuntimeError("No se encontró la tabla de opciones")
        # Buscar el índice de la columna 'ANT.' de forma robusta
        headers = [th.get_text(strip=True).lower() for th in tabla.find_all("th")]
        ant_idx = next((i for i, h in enumerate(headers) if "ant" in h), -1)
        if ant_idx == -1:
            raise Exception("No se encontró columna 'ANT.' en la tabla de opciones")
        hoy = datetime.date.today()
        opciones = []
        for fila in tabla.find_all("tr", {"data-tipo": True}):
            tipo_cod = fila["data-tipo"]
            tipo = "CALL" if tipo_cod.startswith("OCE") else "PUT"
            celdas = fila.find_all("td")
            try:
                strike_raw = celdas[0].get_text(strip=True)
                try:
                    strike = float(strike_raw.replace(".", "").replace(",", "."))
                except Exception as e:
                    print(f"[SCRAPER WARNING] Strike inválido: '{strike_raw}' | Error: {e}")
                    continue  # Si no hay strike, no tiene sentido guardar la fila

                # Extraer el valor de la columna 'ANT.' como precio (última columna)
                precio_raw = celdas[-1].get_text(strip=True) if len(celdas) > 0 else "-"
                print(f"[DEBUG] Strike: {strike}, Valor columna ANT (última columna): '{precio_raw}'")
                try:
                    precio = float(precio_raw.replace(".", "").replace(",", "."))
                except Exception:
                    precio = np.nan  # Si el precio es inválido, lo guardamos como NaN

                fecha_venc = vencimientos.get(tipo_cod)
                if not fecha_venc:
                    print(f"[SCRAPER WARNING] No se encontró fecha de vencimiento para tipo_cod: {tipo_cod}")
                    continue
                dias = (fecha_venc - hoy).days
                opciones.append({
                    "tipo_opcion": tipo,
                    "strike": strike,
                    "precio": precio,
                    "fecha_venc": fecha_venc,
                    "dias_vto": dias
                })
            except Exception as e:
                print(f"[SCRAPER ERROR] Fila no procesada. Error: {e}")
                continue
        return pd.DataFrame(opciones)

class MiniIbexFuturosScraper:
    """
    Scraper para extraer precios de futuros del Mini IBEX desde MEFF.
    """
    URL = "https://www.meff.es/esp/Derivados-Financieros/Ficha/FIEM_MiniIbex_35"

    def __init__(self):
        self.session = requests.Session()

    def fetch_html(self):
        resp = self.session.get(self.URL)
        resp.raise_for_status()
        return resp.text

    def parse_futuros(self, html):
        print("=== TEST VERSION 20240515 ===")
        soup = BeautifulSoup(html, "html.parser")
        tabla = soup.find("table", id="Contenido_Contenido_tblFuturos")
        if not tabla:
            raise RuntimeError("No se encontró la tabla de futuros")
        df = pd.read_html(StringIO(str(tabla)), decimal=",", thousands=".")[0]
        print("Columnas originales del DataFrame de futuros:", df.columns)  # Depuración antes de cualquier cambio
        df = df[df.iloc[:, 0] != "Volumen Total"]
        if isinstance(df.columns[0], tuple):
            df.columns = [c[0].strip().lower() for c in df.columns]
        else:
            df.columns = [c.strip().lower() for c in df.columns]
        df.rename(columns={"vencimiento": "fecha_venc"}, inplace=True)
        print("Columnas del DataFrame de futuros:", df.columns)  # Depuración
        # Buscar la columna que contenga 'ant' (ignorando mayúsculas/minúsculas y el punto)
        ant_col = [c for c in df.columns if 'ant' in c.lower()]
        if not ant_col:
            # Si no se encuentra 'ant', usar la última columna
            print(f"[WARNING] No se encontró columna 'ANT'. Usando última columna: {df.columns[-1]}")
            ant_col = [df.columns[-1]]
        print(f"[DEBUG] Usando columna de precio: {ant_col[0]}")
        print("[DEBUG] Primeros valores de columna seleccionada:", df[ant_col[0]].head())
        df["precio_ultimo"] = df[ant_col[0]].replace('-', np.nan).astype(float)
        df["fecha_venc"] = df["fecha_venc"].apply(lambda x: datetime.datetime.strptime(x.strip(), "%d %b. %Y").date())
        return df[["fecha_venc", "precio_ultimo"]]

    def obtener_futuros(self):
        html = self.fetch_html()
        return self.parse_futuros(html)

print("=== LAMBDA ACTUALIZADA - TEST DE VERSION ===") 