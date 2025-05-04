# Dockerfile para Lambdas en modo contenedor con AWS Lambda runtime
FROM public.ecr.aws/lambda/python:3.9

# Directorio de trabajo donde AWS Lambda ejecuta el código
WORKDIR /var/task

# Copiar y instalar dependencias
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar los scripts de Lambda desde la estructura real
COPY lambda/scraper_lambda.py ./
COPY lambda/iv_lambda.py ./
COPY lambda/scraper/scrape_all_dates_full.py ./
COPY lambda/scraper/meff_scraper.py ./

# Define el handler de arranque para la función scraper
CMD ["scraper_lambda.lambda_handler"]