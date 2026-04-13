FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only production-ready Python modules
COPY shared.py .
COPY dev.py .
COPY main_prod.py .

# Production: FastAPI server with webhooks
# Development: docker-compose.yml overrides with `tail -f /dev/null` + `docker exec ... python dev.py`
CMD ["uvicorn", "main_prod:app", "--host", "0.0.0.0", "--port", "8000"]