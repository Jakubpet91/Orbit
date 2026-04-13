FROM python:3.11-slim

WORKDIR /app

# Install git, openssh-client for SSH operations
RUN apt-get update && apt-get install -y git openssh-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only production-ready Python modules
COPY shared.py .
COPY dev.py .
COPY main.py .
COPY chaos_agent.py .

# Production: FastAPI server with webhooks
# Development: docker-compose.yml overrides with `tail -f /dev/null` + `docker exec ... python dev.py`
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]