# Usa una imagen base con Python 3.11
FROM python:3.11-slim

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos
COPY requirements.txt requirements.txt
COPY app.py app.py
COPY fraud_detection_complete.csv fraud_detection_complete.csv

# Instalar dependencias
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Exponer el puerto
EXPOSE 8080

# Comando de arranque
CMD ["python", "app.py"]
