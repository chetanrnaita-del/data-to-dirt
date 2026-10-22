# Use official lightweight Python image
FROM python:3.11-slim

# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into container
COPY . .

# Expose port (Cloud Run will supply $PORT)
EXPOSE 8080

# Run the web service using Gunicorn
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 "src.app.server:app"
