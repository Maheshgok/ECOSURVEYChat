FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run migrations and start app
CMD ["sh", "-c", "python -c 'from app.core.database import migrate_db; migrate_db()' && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
