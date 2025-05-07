import os
from app.iv_smile_app import csv_scraping
import pandas as pd

if __name__ == "__main__":
    # Scrape IV directly via CSV
    calls_iv, puts_iv = csv_scraping()

    # Ensure output directory exists
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # Export to CSV
    for fecha, df_calls in calls_iv.items():
        safe_date = fecha.replace("/", "-")
        # Eliminar filas con valores no numéricos en Strike (p.ej. encabezados duplicados)
        if 'Strike' in df_calls.columns:
            df_calls = df_calls[df_calls['Strike'].apply(lambda x: pd.to_numeric(str(x).replace('.', '').replace(',', '.'), errors='coerce')).notnull()]
        calls_file = os.path.join(output_dir, f"calls_iv_{safe_date}.csv")
        df_calls.to_csv(calls_file, index=False)
        print(f"Exported Call IV CSV for {fecha}: {calls_file}")

    for fecha, df_puts in puts_iv.items():
        safe_date = fecha.replace("/", "-")
        if 'Strike' in df_puts.columns:
            df_puts = df_puts[df_puts['Strike'].apply(lambda x: pd.to_numeric(str(x).replace('.', '').replace(',', '.'), errors='coerce')).notnull()]
        puts_file = os.path.join(output_dir, f"puts_iv_{safe_date}.csv")
        df_puts.to_csv(puts_file, index=False)
        print(f"Exported Put IV CSV for {fecha}: {puts_file}")

    print("Done. CSV files are in the 'output' directory.") 