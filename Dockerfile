# Dockerfile para la aplicación IV Smile en Streamlit
FROM python:3.9-slim

# Directorio de trabajo
WORKDIR /app

# Copiar dependencias e instalarlas
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar solo el código de la aplicación y scripts principales
COPY app/ ./app/
COPY calculate_iv_from_csv.py ./
COPY export_iv.py ./
COPY export_raw_data.py ./

# Exponer puerto que usará Streamlit
EXPOSE 8501

# Comando de arranque
CMD ["streamlit", "run", "app/iv_smile_app.py", "--server.port", "8501", "--server.address", "0.0.0.0"] 