import time
import pandas as pd
from typing import Dict, Tuple
from .meff_scraper import setup_driver, accept_cookies, parse_tables_from_html, MEFF_URL
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


def scrape_all_dates() -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
    """
    Recorre cada fecha del select OpStrike y devuelve tres dicts:
      - all_futures[fecha]: DataFrame con tabla de Futuros
      - all_calls[fecha]: DataFrame con tabla de Calls
      - all_puts[fecha]:  DataFrame con tabla de Puts
    """
    driver = setup_driver()
    all_futures: Dict[str, pd.DataFrame] = {}
    all_calls:  Dict[str, pd.DataFrame] = {}
    all_puts:   Dict[str, pd.DataFrame] = {}

    try:
        print(f"Navegando a {MEFF_URL}...")
        driver.get(MEFF_URL)

        # Aceptar cookies si aparece el banner
        accept_cookies(driver)

        wait = WebDriverWait(driver, 30)
        # Esperar que la tabla de Futuros cargue para asegurar la página inicial
        wait.until(EC.presence_of_element_located((By.ID, "Contenido_Contenido_tblFuturos")))

        # Localizar select de fechas de expiración (OpStrike)
        sel_elem = wait.until(EC.element_to_be_clickable((By.ID, "OpStrike")))
        select = Select(sel_elem)

        # Obtener todas las fechas disponibles
        expiration_options = [
            (opt.text.strip(), opt.get_attribute("value"))
            for opt in select.options
            if opt.get_attribute("value")
        ]
        print("Fechas encontradas:", [t for t, _ in expiration_options])

        # Iterar sobre cada fecha de expiración
        for fecha_texto, fecha_val in expiration_options:
            print(f"--- Procesando fecha: {fecha_texto} ---")
            select.select_by_value(fecha_val)

            # Esperar que el select quede obsoleto y volver a localizarlo
            try:
                wait.until(EC.staleness_of(sel_elem))
            except:
                pass
            sel_elem = wait.until(EC.element_to_be_clickable((By.ID, "OpStrike")))
            select = Select(sel_elem)

            # Esperar que la tabla de Opciones (tblOpciones) se recargue
            wait.until(EC.presence_of_element_located((By.ID, "tblOpciones")))
            time.sleep(1)

            # Parsear HTML actual para Futuros, Calls y Puts
            f_df, calls_df, puts_df = parse_tables_from_html(driver.page_source)

            if f_df is not None:
                all_futures[fecha_texto] = f_df
            if calls_df is not None:
                all_calls[fecha_texto] = calls_df
            if puts_df is not None:
                all_puts[fecha_texto] = puts_df

        return all_futures, all_calls, all_puts

    except Exception as e:
        print("Error en scrape_all_dates:", e)
        return {}, {}, {}

    finally:
        print("Cerrando WebDriver...")
        driver.quit()


if __name__ == "__main__":
    futures, calls, puts = scrape_all_dates()

    print("\n--- Resumen por Fechas ---")
    for fecha in futures:
        f = futures[fecha]
        c = calls.get(fecha)
        p = puts.get(fecha)
        print(f"{fecha}: Futures={len(f) if f is not None else 0}, Calls={len(c) if c is not None else 0}, Puts={len(p) if p is not None else 0}")

    # Ejemplo de primeras filas para la primera fecha
    if futures:
        primera = next(iter(futures))
        print(f"\nEjemplo Futures para {primera}:")
        print(futures[primera].head().to_string(index=False))
    if calls:
        print(f"\nEjemplo Calls para {primera}:")
        print(calls[primera].head().to_string(index=False))
    if puts and primera in puts:
        print(f"\nEjemplo Puts para {primera}:")
        print(puts[primera].head().to_string(index=False))

# Para ejecutar este script:
# cd "C:\Users\User\Desktop\PRACTICA AWS"
# python -m scraper.scrape_all_dates