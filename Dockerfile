FROM python:3.11-slim

# FFmpeg, Node.js ve gerekli sistem araçlarını kur
# Node.js, yt-dlp'nin YouTube JS meydan okumalarını (n-challenge) çözmesi için gereklidir
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python bağımlılıklarını kur
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -U yt-dlp

# Backend kodlarını kopyala
COPY backend/ .

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
