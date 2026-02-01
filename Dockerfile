FROM python:3.11-slim

WORKDIR /app

# Copy backend files
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Expose port
EXPOSE 8080

# Run migrations and start server
CMD python -c "from app.core.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine); print('✓ Database initialized')" && \
    uvicorn app.main:app --host 0.0.0.0 --port 8080
