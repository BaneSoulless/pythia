FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt /app/src/
RUN pip install --no-cache-dir -r requirements.txt

# Copia l'applicazione (dopo la migrazione)
COPY ./src /app/src

# Set PYTHONPATH
ENV PYTHONPATH=/app/src

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Command: updated per la nuova struttura src/pythia/api/v1/main.py (o dove risiede)
CMD ["uvicorn", "pythia.api.v1.main:app", "--host", "0.0.0.0", "--port", "8000"]
