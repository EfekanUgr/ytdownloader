#!/usr/bin/env bash
# ============================================================
# Downloader(+) — Render Backend Build Script
# Ensures FFmpeg and Python dependencies are installed
# ============================================================

set -e

echo "=== [1/3] Python Bağımlılıkları Yükleniyor ==="
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -U yt-dlp

echo "=== [2/3] FFmpeg Kontrolü ==="
if command -v ffmpeg &> /dev/null; then
    echo "✔ Sistem FFmpeg bulundu: $(which ffmpeg)"
else
    echo "⚠ FFmpeg sistemde bulunamadı. Statik Linux FFmpeg ikilisi indiriliyor..."
    mkdir -p ffmpeg_bin
    if [ ! -f ffmpeg_bin/ffmpeg ]; then
        curl -L https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz | tar -xJ --strip-components=2 -C ffmpeg_bin --wildcards '*/bin/ffmpeg' '*/bin/ffprobe' || true
    fi
    chmod +x ffmpeg_bin/* 2>/dev/null || true
    export PATH="$(pwd)/ffmpeg_bin:$PATH"
    echo "✔ Statik FFmpeg hazırlandı."
fi

echo "=== [3/3] Derleme Başarıyla Tamamlandı! ==="
