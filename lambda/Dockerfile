# Usa el runtime de AWS Lambda para Python
FROM public.ecr.aws/lambda/python:3.9
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /var/task

# Copia e instala dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# (Opcional: elimina la parte de Chrome/Chromedriver si ya no usas Selenium)

# Copiar el paquete scraper completo
COPY scraper ./scraper/

# Copiar los entry-points
COPY scraper_lambda.py .
COPY iv_lambda.py .

# Handler de arranque
CMD ["scraper_lambda.lambda_handler"]