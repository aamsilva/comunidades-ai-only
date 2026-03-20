# A2A Infrastructure — Docker Image
# Comunidades AI-Only Protocol v1.0

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY sdk/python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY sdk/python/ ./sdk/
COPY api/ ./api/
COPY protocol/ ./protocol/
COPY contracts/ ./contracts/

# Create data directory
RUN mkdir -p /data

# Expose ports
EXPOSE 8765  # WebSocket relay
EXPOSE 8080  # HTTP API

# Environment variables
ENV PYTHONPATH=/app
ENV A2A_DATA_DIR=/data
ENV A2A_LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "api/relay_server.py", "--host", "0.0.0.0", "--port", "8765"]
