import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO

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
        hoy = datetime.date.today()
        opciones = []
        for fila in tabla.find_all("tr", {"data-tipo": True}):
            tipo_cod = fila["data-tipo"]
            tipo = "CALL" if tipo_cod.startswith("OCE") else "PUT"
            celdas = fila.find_all("td")
            try:
                strike = float(celdas[0].get_text(strip=True).replace(".", "").replace(",", "."))
                precio = float(celdas[12].get_text(strip=True).replace(".", "").replace(",", "."))
                fecha_venc = vencimientos.get(tipo_cod)
                if not fecha_venc:
                    continue
                dias = (fecha_venc - hoy).days
                opciones.append({
                    "tipo_opcion": tipo,
                    "strike": strike,
                    "precio": precio,
                    "fecha_venc": fecha_venc,
                    "dias_vto": dias
                })
            except Exception:
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
        soup = BeautifulSoup(html, "html.parser")
        tabla = soup.find("table", id="Contenido_Contenido_tblFuturos")
        if not tabla:
            raise RuntimeError("No se encontró la tabla de futuros")
        df = pd.read_html(StringIO(str(tabla)), decimal=",", thousands=".")[0]
        df = df[df.iloc[:, 0] != "Volumen Total"]

        # Normaliza nombres de columnas
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Toma la primera columna como fecha de vencimiento
        df.rename(columns={df.columns[0]: "fecha_venc"}, inplace=True)
        # Toma la última columna como precio (ANT) y la llama 'Ant'
        df["Ant"] = df[df.columns[-1]]

        # Convierte fecha y precio
        df["fecha_venc"] = df["fecha_venc"].apply(lambda x: datetime.datetime.strptime(str(x).strip(), "%d %b. %Y").date())
        df["Ant"] = pd.to_numeric(df["Ant"], errors="coerce")

        # Devuelve solo las columnas relevantes
        return df[["fecha_venc", "Ant"]]

    def obtener_futuros(self):
        html = self.fetch_html()
        return self.parse_futuros(html) 