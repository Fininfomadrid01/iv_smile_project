import os
import pandas as pd
from scraper.scrape_all_dates_full import scrape_all_dates_full

if __name__ == "__main__":
    # Directorio de salida para datos crudos
    output_dir = os.path.join("output", "raw")
    os.makedirs(output_dir, exist_ok=True)

    # 1) Scrape de todas las fechas
    futures, calls, puts = scrape_all_dates_full()

    # 2) Exportar DataFrames crudos a CSV
    for fecha, df in futures.items():
        safe_date = fecha.replace("/", "-")
        path = os.path.join(output_dir, f"futures_{safe_date}.csv")
        df.to_csv(path, index=False)
        print(f"Exportados futuros {fecha}: {path}")

    for fecha, df in calls.items():
        safe_date = fecha.replace("/", "-")
        path = os.path.join(output_dir, f"calls_{safe_date}.csv")
        df.to_csv(path, index=False)
        print(f"Exportadas calls {fecha}: {path}")

    for fecha, df in puts.items():
        safe_date = fecha.replace("/", "-")
        path = os.path.join(output_dir, f"puts_{safe_date}.csv")
        df.to_csv(path, index=False)
        print(f"Exportadas puts {fecha}: {path}")

    print("Datos crudos guardados en output/raw/") 