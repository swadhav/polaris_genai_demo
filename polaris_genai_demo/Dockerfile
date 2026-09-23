FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY frontend/dist /app/frontend/dist
COPY frontend/server /app/frontend/server
COPY scripts /app/scripts
COPY models /app/models
COPY dealers /app/dealers
COPY generate_360_videos.py /app/

# Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PROJECT_ID=polaris-genai-demo
ENV GCS_BUCKET=polaris-demo-files
ENV LOCATION=us-central1

EXPOSE 8080

CMD ["python3", "/app/frontend/server/api_server.py"]
