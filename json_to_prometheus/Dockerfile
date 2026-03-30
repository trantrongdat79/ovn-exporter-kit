# Dockerfile for json_to_prometheus component
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY json_to_prometheus/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy common utilities
COPY common/ /app/common/

# Copy component source code
COPY json_to_prometheus/src/ /app/src/

# Create logs directory
RUN mkdir -p /app/logs/json_to_prometheus

# Expose Prometheus metrics port
EXPOSE 8001

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "src/main.py"]
