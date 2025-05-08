from scraper.meff_scraper_classes import MiniIbexFuturosScraper

scraper = MiniIbexFuturosScraper()
df_futuros = scraper.obtener_futuros()
print(df_futuros) 