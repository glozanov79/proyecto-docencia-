FROM python:3.11-slim

WORKDIR /app

# Copiar requirements
COPY agenda/requirements-whatsapp.txt requirements.txt

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY agenda/scripts/whatsapp_bot.py .
COPY agenda/config/tokens.json ./tokens.json

# Exponer puerto
EXPOSE 8080

# Ejecutar bot
CMD exec gunicorn --bind :8080 --workers 1 --timeout 0 whatsapp_bot:app
