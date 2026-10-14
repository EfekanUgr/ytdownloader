#!/usr/bin/env bash
# ============================================================
# Downloader(+) — Render & Linux Native Build Script
# Ensures FFmpeg, Node.js and Python dependencies are installed
# ============================================================

set -e

echo "=== [1/3] Python Bağımlılıkları Yükleniyor ==="
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
pip install -U yt-dlp

echo "=== [2/3] FFmpeg Kontrolü ==="
if command -v ffmpeg &> /dev/null; then
    echo "✔ Sistem FFmpeg bulundu: $(which ffmpeg)"
else
    echo "⚠ FFmpeg sistemde bulunamadı. Statik Linux FFmpeg ikilisi indiriliyor..."
    mkdir -p backend/ffmpeg_bin
    if [ ! -f backend/ffmpeg_bin/ffmpeg ]; then
        curl -L https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz | tar -xJ --strip-components=2 -C backend/ffmpeg_bin --wildcards '*/bin/ffmpeg' '*/bin/ffprobe' || true
    fi
    chmod +x backend/ffmpeg_bin/* 2>/dev/null || true
    export PATH="$(pwd)/backend/ffmpeg_bin:$PATH"
    echo "✔ Statik FFmpeg hazırlandı."
fi

echo "=== [3/3] Derleme Başarıyla Tamamlandı! ==="
