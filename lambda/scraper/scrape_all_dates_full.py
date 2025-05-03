import time
import pandas as pd
from typing import Dict, Tuple
from .meff_scraper import setup_driver, accept_cookies, parse_tables_from_html, MEFF_URL
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


def scrape_all_dates_full() -> Tuple[
    Dict[str, pd.DataFrame],
    Dict[str, pd.DataFrame],
    Dict[str, pd.DataFrame]
]:
    """
    Recorre cada fecha del select OpStrike y devuelve tres diccionarios:
      - all_futures[fecha]: DataFrame con tabla de Futuros
      - all_calls[fecha]:   DataFrame con tabla de Calls
      - all_puts[fecha]:    DataFrame con tabla de Puts
    """
    driver = setup_driver()
    all_futures: Dict[str, pd.DataFrame] = {}
    all_calls:   Dict[str, pd.DataFrame] = {}
    all_puts:    Dict[str, pd.DataFrame] = {}

    try:
        print(f"Navegando a {MEFF_URL}...")
        driver.get(MEFF_URL)

        accept_cookies(driver)

        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.ID, "Contenido_Contenido_tblFuturos")))

        sel = wait.until(EC.element_to_be_clickable((By.ID, "OpStrike")))
        dropdown = Select(sel)
        expiration_options = [
            (opt.text.strip(), opt.get_attribute("value"))
            for opt in dropdown.options if opt.get_attribute("value")
        ]
        print("Fechas encontradas:", [t for t, _ in expiration_options])

        for fecha, valor in expiration_options:
            print(f"--- Procesando fecha: {fecha} ---")
            dropdown.select_by_value(valor)
            try:
                wait.until(EC.staleness_of(sel))
            except:
                pass
            sel = wait.until(EC.element_to_be_clickable((By.ID, "OpStrike")))
            dropdown = Select(sel)

            # Espera recarga futuros y opciones
            wait.until(EC.presence_of_element_located((By.ID, "Contenido_Contenido_tblFuturos")))
            wait.until(EC.presence_of_element_located((By.ID, "tblOpciones")))
            time.sleep(1)

            html = driver.page_source
            f_df, c_df, p_df = parse_tables_from_html(html)

            if f_df is not None:
                all_futures[fecha] = f_df
            if c_df is not None:
                all_calls[fecha]  = c_df
            if p_df is not None:
                all_puts[fecha]   = p_df

        return all_futures, all_calls, all_puts

    except Exception as e:
        print("Error en scrape_all_dates_full:", e)
        return {}, {}, {}

    finally:
        print("Cerrando WebDriver...")
        driver.quit()


if __name__ == "__main__":
    futures, calls, puts = scrape_all_dates_full()
    print("\n--- Resumen por Fechas (Full) ---")
    for fecha in futures:
        f = futures[fecha]
        c = calls.get(fecha)
        p = puts.get(fecha)
        print(
            f"{fecha}: Futures={len(f) if f is not None else 0},"
            f" Calls={len(c) if c is not None else 0},"
            f" Puts={len(p) if p is not None else 0}"
        )
    if futures:
        primera = next(iter(futures))
        print(f"\nEjemplo Futures para {primera}:")
        print(futures[primera].head().to_string(index=False))
        print(f"\nEjemplo Calls para {primera}:")
        print(calls[primera].head().to_string(index=False))
        print(f"\nEjemplo Puts para {primera}:")
        print(puts[primera].head().to_string(index=False))

# Para ejecutar:
# cd "C:\Users\User\Desktop\PRACTICA AWS"
# python -m scraper.scrape_all_dates_full 