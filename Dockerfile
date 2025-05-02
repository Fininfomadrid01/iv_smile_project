# Dockerfile para la aplicación IV-Smile con Streamlit
FROM python:3.9-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar y instalar dependencias
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY app/ ./app/

# Exponer el puerto que usará Streamlit
EXPOSE 8501

# Comando de arranque
CMD ["streamlit", "run", "app/iv_smile_app.py", \
     "--server.port", "8501", "--server.address", "0.0.0.0"]