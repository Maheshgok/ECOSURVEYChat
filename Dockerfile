FROM python:3.11-slim

WORKDIR /app

# Copy backend files
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Expose port
EXPOSE 8080

# Run server (skip database init for cloud deployments without PostgreSQL)
CMD uvicorn app.main:app --host 0.0.0.0 --port 8080
