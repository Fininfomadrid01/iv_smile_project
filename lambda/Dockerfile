# iv_smile_project/lambda/Dockerfile

# Usa el runtime de AWS Lambda para Python
FROM public.ecr.aws/lambda/python:3.9
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Directorio de trabajo (donde Lambda carga tu código)
WORKDIR /var/task

# Copia e instala tus dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala dependencias básicas y Chrome
RUN yum update -y && \
    yum install -y unzip xorg-x11-server-Xvfb libXfont2 alsa-lib gtk3 libXtst pango-devel && \
    curl -sS -L https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm -o /tmp/google-chrome.rpm && \
    yum install -y /tmp/google-chrome.rpm && rm -f /tmp/google-chrome.rpm

# Descarga y configura Chromedriver emparejado o con fallback
RUN set -eux; \
    CHROME_VERSION="$(google-chrome --version | awk '{print $3}')"; \
    CHROME_MAJOR="${CHROME_VERSION%%.*}"; \
    echo "Chrome version: $CHROME_VERSION (major $CHROME_MAJOR)"; \
    URL_MAJOR="https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR}"; \
    if ! curl -fsSL "$URL_MAJOR" -o /tmp/driver_version; then \
      echo "No chromedriver for major $CHROME_MAJOR, using LATEST_RELEASE"; \
      curl -fsSL "https://chromedriver.storage.googleapis.com/LATEST_RELEASE" -o /tmp/driver_version; \
    fi; \
    CHROMEDRIVER_VERSION="$(cat /tmp/driver_version)"; \
    echo "Chromedriver version: $CHROMEDRIVER_VERSION"; \
    curl -fsSL "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" -o /tmp/chromedriver.zip; \
    unzip -q /tmp/chromedriver.zip -d /usr/local/bin; \
    chmod +x /usr/local/bin/chromedriver; \
    rm -f /tmp/chromedriver.zip /tmp/driver_version; \
    ln -sf /usr/bin/google-chrome-stable /usr/bin/google-chrome

# Copiar el paquete scraper completo
COPY lambda/scraper ./scraper/

# Copiar los entry-points
COPY lambda/scraper_lambda.py .
COPY lambda/iv_lambda.py        .

# Handler de arranque
CMD ["scraper_lambda.lambda_handler"]