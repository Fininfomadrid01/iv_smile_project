import sys, os
# Asegurar que el folder actual (app/) esté en sys.path para encontrar el módulo meff_scraper_classes
sys.path.insert(0, os.path.dirname(__file__))
from meff_scraper_classes import MeffScraper, FuturosScraper

if __name__ == '__main__':
    print('=== Test de FuturosScraper ===')
    fs = FuturosScraper()
    df_fut = fs.obtener_datos_futuros()
    print('\n-- Futuros obtenidos:')
    print(df_fut)

    print('\n=== Test de MeffScraper ===')
    ms = MeffScraper()
    df_ops = ms.obtener_datos_opciones()
    print('\n-- Primeras 5 filas de opciones:')
    print(df_ops.head())
    # Lista de fechas de vencimiento únicas
    print('\n-- Fechas de vencimiento (únicas):')
    print(sorted(df_ops['fecha_venc'].unique()))
    # Conteo de opciones por fecha y tipo
    print('\n-- Conteo por fecha y tipo de opción:')
    print(df_ops.groupby(['fecha_venc', 'tipo_opcion']).size())
    # Estadísticos de strikes
    print('\n-- Estadísticos de strike:')
    print(df_ops['strike'].describe())
    # Descomenta para ver todos los registros
    # print(df_ops) 