# api/ backend image. Builds the FastAPI app for production; expects
# DATABASE_URL to point at a real PostgreSQL instance (see
# docker-compose.yml, which wires this to the `db` service).
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
