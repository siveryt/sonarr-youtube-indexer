FROM python:3.11-slim

LABEL maintainer="Ioannis Kokkinis"
LABEL description="YouTube Indexer for Prowlarr/Sonarr - Torznab-compatible API"

# Install yt-dlp
RUN pip install --no-cache-dir yt-dlp

# Create app directory
WORKDIR /app

# Copy application
COPY youtube_indexer.py /app/

# Expose port
EXPOSE 9117

CMD ["python", "-u", "youtube_indexer.py"]
