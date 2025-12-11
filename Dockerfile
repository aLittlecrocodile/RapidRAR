# Multi-arch Dockerfile for RapidRAR
# Supports amd64 and arm64

# Use slim python image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
# unrar: Required for RAR file handling (non-free)
# build-essential: Required for compiling some python packages
# git: Useful for some pip installs
RUN echo "deb http://deb.debian.org/debian bookworm non-free" >> /etc/apt/sources.list.d/non-free.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    unrar \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create volume mount points for data
VOLUME /data

# Default entrypoint
# Expose API port (optional for CLI, but good for docs)
EXPOSE 8000

# Default entrypoint (CLI)
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
