import os
import glob
import pandas as pd
from scraper.volatility import parse_spanish_date, add_implied_volatility

# Directorio de CSVs crudos
RAW_DIR = os.path.join("output", "raw")
# Directorio de salida para CSVs con la IV
IV_DIR  = os.path.join("output", "iv")

if __name__ == "__main__":
    # Crear carpeta de salida si no existe
    os.makedirs(IV_DIR, exist_ok=True)

    # Patrón para todos los CSV de futuros
    pattern = os.path.join(RAW_DIR, "futures_*.csv")
    for fut_path in glob.glob(pattern):
        # Extraer fecha del nombre de archivo: futures_YYYY-MM-DD.csv → YYYY-MM-DD
        filename = os.path.basename(fut_path)
        fecha = filename.replace("futures_", "").replace(".csv", "")

        # 1) Leer DataFrame de futuros
        df_fut = pd.read_csv(fut_path, sep=",", decimal=".")
        # Detectar columna ANT y extraer primer valor numérico válido
        ant_cols = [c for c in df_fut.columns if "ANT" in c.upper()]
        if not ant_cols:
            print(f"No se encontró columna ANT en {filename}. Saltando fecha {fecha}.")
            continue
        nums = (
            pd.to_numeric(
                df_fut[ant_cols[-1]].astype(str)
                      .str.replace(".", "", regex=False)
                      .str.replace(",", ".", regex=False),
                errors="coerce"
            )
            .dropna()
        )
        if nums.empty:
            print(f"Precio futuro inválido para {fecha}. Saltando.")
            continue
        future_price = float(nums.iloc[0])
        # Parsear la fecha de expiración (formato español o dd/mm/YYYY)
        expiry_dt = parse_spanish_date(fecha.replace("-", "/"))

        # 2) Procesar CALLS
        calls_file = os.path.join(RAW_DIR, f"calls_{fecha}.csv")
        if os.path.exists(calls_file):
            # Leer saltando la segunda fila de cabecera duplicada
            df_calls = pd.read_csv(
                calls_file,
                sep=",",
                decimal=".",
                skiprows=[1]
            )
            # Quitar filas con “Strike” literal o “Volumen Total”
            df_calls = df_calls[~df_calls["Strike"].isin(["Strike", "Volumen Total"])]

            # Calcular IV para calls
            df_calls_iv = add_implied_volatility(
                df_calls,
                future_price,
                expiry_dt,
                "call"
            )
            out_calls = os.path.join(IV_DIR, f"calls_iv_{fecha}.csv")
            df_calls_iv.to_csv(out_calls, index=False)
            print(f"Calls IV guardado para {fecha}: {out_calls}")
        else:
            print(f"No existe el archivo de calls para {fecha}: {calls_file}")

        # 3) Procesar PUTS
        puts_file = os.path.join(RAW_DIR, f"puts_{fecha}.csv")
        if os.path.exists(puts_file):
            df_puts = pd.read_csv(
                puts_file,
                sep=",",
                decimal=".",
                skiprows=[1]
            )
            df_puts = df_puts[~df_puts["Strike"].isin(["Strike", "Volumen Total"])]

            df_puts_iv = add_implied_volatility(
                df_puts,
                future_price,
                expiry_dt,
                "put"
            )
            out_puts = os.path.join(IV_DIR, f"puts_iv_{fecha}.csv")
            df_puts_iv.to_csv(out_puts, index=False)
            print(f"Puts IV guardado para {fecha}: {out_puts}")
        else:
            print(f"No existe el archivo de puts para {fecha}: {puts_file}")

    print("Cálculo de IV completado. Archivos generados en output/iv/")