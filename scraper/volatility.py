import mibian
import pandas as pd
from datetime import datetime
from typing import Dict, Tuple

# Map abreviaturas españolas a números de mes
SPANISH_MONTHS = {
    'ene.': 1, 'feb.': 2, 'mar.': 3, 'abr.': 4,
    'may.': 5, 'jun.': 6, 'jul.': 7, 'ago.': 8,
    'sep.': 9, 'oct.': 10,'nov.': 11,'dic.': 12
}

def parse_spanish_date(date_str: str) -> datetime:
    """
    Convierte '16 may. 2025' o '16/05/2025' en datetime(2025,5,16).
    """
    # Intento formato numérico 'dd/mm/yyyy'
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except Exception:
        pass
    # Fallback para nombres de mes en español '16 may. 2025'
    parts = date_str.lower().split()
    if len(parts) != 3:
        raise ValueError(f"Fecha inválida: {date_str}")
    day = int(parts[0])
    month = SPANISH_MONTHS.get(parts[1])
    year = int(parts[2])
    if month is None:
        raise ValueError(f"Mes inválido en fecha: {date_str}")
    return datetime(year, month, day)


def add_implied_volatility(
    df: pd.DataFrame,
    future_price: float,
    expiry_dt: datetime,
    option_type: str
) -> pd.DataFrame:
    """
    Añade las columnas 'IV_raw' e 'IV' al DataFrame de Calls o Puts.
    option_type: 'call' o 'put'.
    - IV_raw: valor bruto devuelto por MibianLib (puede alcanzar 500).
    - IV: mismo valor, pero convertido a None si IV_raw >= 500.
    """
    # Detectar columnas de Strike y ANT en el DataFrame
    cols = df.columns
    strike_cols = [c for c in cols if 'STRIKE' in c.upper()]
    ant_cols    = [c for c in cols if 'ANT'    in c.upper()]
    if not strike_cols or not ant_cols:
        raise KeyError(f"No se encontraron columnas Strike/Ant en el DataFrame: {cols}")
    strike_col = strike_cols[0]
    ant_col    = ant_cols[-1]

    # Días hasta vencimiento
    days = max((expiry_dt - datetime.now()).days, 1)  # al menos 1 día

    # Arrays para guardar calcs
    iv_raw_list = []
    iv_list     = []

    for _, row in df.iterrows():
        try:
            # Extraer y convertir Strike
            raw_strike = str(row[strike_col])
            strike = float(raw_strike.replace('.', '').replace(',', '.'))

            # Extraer y convertir precio ANT de la opción
            raw_price = row[ant_col]
            if isinstance(raw_price, (int, float)):
                price = float(raw_price)
            else:
                price = float(str(raw_price).replace('.', '').replace(',', '.'))

            # Calcular volatilidad implícita con Black-Scholes y r=0
            if option_type.lower() == 'call':
                bs = mibian.BS([future_price, strike, 0, days], callPrice=price)
            else:
                bs = mibian.BS([future_price, strike, 0, days], putPrice=price)

            # Obtener IV bruto y añadir debug
            iv = bs.impliedVolatility
            iv_raw_list.append(iv)
            print(f"[IV DEBUG] strike={strike}, price={price}, future={future_price}, days={days}, iv_raw={iv}")

            # Filtrar IV final: None si el solver llegó a 500
            iv_list.append(iv if iv < 500 else None)

        except Exception:
            # En caso de error en conversión o en MibianLib, guardo None
            iv_raw_list.append(None)
            iv_list.append(None)

    # Construir DataFrame de salida con ambas columnas
    out = df.copy()
    out['IV_raw'] = iv_raw_list
    out['IV']     = iv_list
    # Añadir columna con días hasta vencimiento para futura filtración
    out['Days']   = days
    return out


def calculate_iv_all(
    all_futures: Dict[str, pd.DataFrame],
    all_calls:  Dict[str, pd.DataFrame],
    all_puts:   Dict[str, pd.DataFrame]
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
    """
    Dados los dicts de scraping:
      - all_futures[fecha], all_calls[fecha], all_puts[fecha]
    devuelve dos dicts:
      - calls_iv[fecha]: DataFrame de Calls con IV
      - puts_iv[fecha]:  DataFrame de Puts con IV
    """
    calls_iv = {}
    puts_iv  = {}

    # Procesar CALLS
    for fecha, calls_df in all_calls.items():
        expiry = parse_spanish_date(fecha)
        fut_df = all_futures.get(fecha)
        if fut_df is None or fut_df.empty:
            continue

        # Extraer precio ANT del futuro
        ant_cols = [c for c in fut_df.columns if 'ANT' in c.upper()]
        if not ant_cols:
            raise KeyError(f"No se encontró columna 'ANT' en futuros para {fecha}. Columnas: {fut_df.columns.tolist()}")
        ant_col = ant_cols[-1]

        nums = pd.to_numeric(
            fut_df[ant_col].astype(str)
                  .str.replace('.', '',    regex=False)
                  .str.replace(',', '.',   regex=False),
            errors='coerce'
        ).dropna()
        if nums.empty:
            raise ValueError(f"No se encontró valor numérico válido en columna '{ant_col}' para {fecha}.")
        future_price = float(nums.iloc[0])

        # Calcular IV para calls
        calls_iv[fecha] = add_implied_volatility(calls_df, future_price, expiry, 'call')

    # Procesar PUTS
    for fecha, puts_df in all_puts.items():
        expiry = parse_spanish_date(fecha)
        fut_df = all_futures.get(fecha)
        if fut_df is None or fut_df.empty:
            continue

        ant_cols = [c for c in fut_df.columns if 'ANT' in c.upper()]
        if not ant_cols:
            raise KeyError(f"No se encontró columna 'ANT' en futuros para {fecha}. Columnas: {fut_df.columns.tolist()}")
        ant_col = ant_cols[-1]

        nums = pd.to_numeric(
            fut_df[ant_col].astype(str)
                  .str.replace('.', '',    regex=False)
                  .str.replace(',', '.',   regex=False),
            errors='coerce'
        ).dropna()
        if nums.empty:
            raise ValueError(f"No se encontró valor numérico válido en columna '{ant_col}' para {fecha}.")
        future_price = float(nums.iloc[0])

        # Calcular IV para puts
        puts_iv[fecha] = add_implied_volatility(puts_df, future_price, expiry, 'put')

    return calls_iv, puts_iv