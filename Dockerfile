# Multi-stage build for smaller final image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
# unrar-free is widely available but often fails with newer RARs. 
# We try to install unrar-nonfree if possible, otherwise unrar-free.
# We also install p7zip-full as a fallback for patool.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    p7zip-full \
    unrar-free \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for cache optimization
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install the package globally
RUN pip install .

# Expose port
EXPOSE 8000

# Run the API
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
