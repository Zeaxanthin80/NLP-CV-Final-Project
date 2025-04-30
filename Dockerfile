FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    redis-server \
    ffmpeg \
    libsm6 \
    libxext6 \
    git \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install latest pytube for better YouTube support
RUN pip install --no-cache-dir --upgrade pytube

# Copy application code
COPY . .

# Download NLTK data
RUN python download_nltk_data.py

# Create a script to start all services
RUN echo '#!/bin/bash\n\
# Start Redis server\nredis-server --daemonize yes\n\
# Wait for Redis to be ready\nsleep 2\n\
# Start Celery worker\ncelery -A celery_worker.celery worker --loglevel=info &\n\
# Wait for Celery to be ready\nsleep 3\n\
# Start Flask application\ngunicorn main:app --bind 0.0.0.0:7860\n' > start.sh

RUN chmod +x start.sh

# Expose the port the app runs on
EXPOSE 7860

# Command to run the application
CMD ["./start.sh"]
