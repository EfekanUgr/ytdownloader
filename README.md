# Downloader(+) — Video & Müzik İndirici

YouTube ve desteklenen platformlardan yüksek kaliteli video (MP4) ve müzik (320 kbps MP3) indirme uygulaması.

---

## 📁 Proje Mimarisi

* **`dist/`** — **Netlify** üzerinde barındırılan modern, responsive (mobil uyumlu) tek sayfalık web arayüzü.
* **`backend/`** — **Render.com** üzerinde Docker ile çalışan FastAPI tabanlı indirme motoru (FFmpeg ve yt-dlp entegreli).
* **CLI Başlatıcıları** (`video.bat`, `muzik.bat`, `altyazi.bat`, `indirici.py`) — Windows kullanıcıları için doğrudan masaüstünden tek tıkla indirme araçları.

---

## ⚡ Canlı Dağıtım (CI/CD)

* **Render.com:** Bu repodaki `backend` klasörünü izler. Yeni bir commit geldiğinde Docker konteynerini otomatik olarak yeniden derler ve canlıya alır.
* **Netlify:** Bu repodaki `dist` klasörünü yayın dizini (publish directory) olarak sunar.
