# Dockerfile for raw_to_json component
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY raw_to_json/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy common utilities
COPY common/ /app/common/

# Copy component source code
COPY raw_to_json/src/ /app/src/

# Create logs directory
RUN mkdir -p /app/logs/raw_to_json

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "src/main.py"]
