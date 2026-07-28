FROM python:3.13-slim

WORKDIR /app

# Copiamos e instalamos dependencias primero para aprovechar el caché
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código del backend
COPY . .

# Railway inyecta la variable PORT, por lo que usamos $PORT de forma dinámica
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]