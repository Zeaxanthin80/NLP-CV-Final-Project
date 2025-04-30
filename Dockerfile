FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python download_nltk_data.py

# Install Redis
RUN apt-get update && apt-get install -y redis-server

# Create a script to start all services
RUN echo '#!/bin/bash\nredis-server --daemonize yes\ncelery -A celery_worker.celery worker --loglevel=info &\ngunicorn main:app --bind 0.0.0.0:7860\n' > start.sh
RUN chmod +x start.sh

EXPOSE 7860

CMD ["./start.sh"]
