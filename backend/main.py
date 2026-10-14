# -*- coding: utf-8 -*-
"""
Downloader(+) REST API — FastAPI tabanlı video, müzik ve altyazı indirme sunucusu.
Render, Railway, Docker veya yerel ortamda çalışmak üzere optimize edilmiştir.
"""

import asyncio
import base64
import json
import logging
import os
import re
import shutil
import subprocess
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, HttpUrl
import yt_dlp
from yt_dlp.postprocessor import PostProcessor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("downloader-api")

app = FastAPI(
    title="Downloader(+) API",
    description="YouTube ve web platformları için yüksek hızlı video, müzik ve altyazı indirme servisi",
    version="1.3.0"
)

# CORS — Netlify ve tüm web istemcileri için açık
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)

# Dizinler
BASE_DIR = Path(__file__).resolve().parent
TEMP_DOWNLOAD_DIR = BASE_DIR / "temp_downloads"
TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Yerel Windows ortamında 'araçlar/ffmpeg' varsa kullan, yoksa sistem PATH'ine güven
LOCAL_FFMPEG = BASE_DIR.parent / "araçlar" / "ffmpeg"
if (LOCAL_FFMPEG / "ffmpeg.exe").exists():
    os.environ["PATH"] = str(LOCAL_FFMPEG) + os.pathsep + os.environ.get("PATH", "")

# Linux static build fallback (build.sh tarafından indirilmişse)
LINUX_FFMPEG = BASE_DIR / "ffmpeg_bin"
if (LINUX_FFMPEG / "ffmpeg").exists():
    os.environ["PATH"] = str(LINUX_FFMPEG) + os.pathsep + os.environ.get("PATH", "")

# Görev durumu deposu
executor = ThreadPoolExecutor(max_workers=3)
tasks: Dict[str, Dict[str, Any]] = {}


def find_ffmpeg_path() -> Optional[str]:
    """Sistemde ffmpeg var mı kontrol et."""
    if (LOCAL_FFMPEG / "ffmpeg.exe").exists():
        return str(LOCAL_FFMPEG)
    if (LINUX_FFMPEG / "ffmpeg").exists():
        return str(LINUX_FFMPEG)
    if shutil.which("ffmpeg"):
        return str(Path(shutil.which("ffmpeg")).parent)
    return None


def _get_cookiefile() -> Optional[str]:
    """cookies.txt dosyası veya Render/Railway YOUTUBE_COOKIES çevre değişkenini yükler."""
    candidate_paths = [
        BASE_DIR / "cookies.txt",
        BASE_DIR.parent / "cookies.txt",
        Path("/etc/secrets/cookies.txt"),
        Path("/etc/secrets/youtube_cookies.txt"),
        Path("/etc/secrets/cookies"),
        Path.home() / "cookies.txt",
    ]
    for p in candidate_paths:
        try:
            if p.exists() and p.stat().st_size > 50:
                return str(p)
        except Exception:
            pass
    
    for env_key in ("YOUTUBE_COOKIES", "COOKIES", "COOKIE"):
        env_content = os.environ.get(env_key)
        if env_content and len(env_content.strip()) > 30:
            cf = BASE_DIR / "env_cookies.txt"
            try:
                content = env_content.strip()
                # Eğer Base64 ile kodlanmışsa çöz
                try:
                    decoded = base64.b64decode(content).decode("utf-8")
                    if "youtube.com" in decoded or "VISITOR" in decoded:
                        content = decoded
                except Exception:
                    pass

                # Literal \n kaçışlarını gerçek satır sonuna çevir
                if "\\n" in content and "\n" not in content:
                    content = content.replace("\\n", "\n")

                # Netscape başlığı eksikse ekle
                if not content.startswith("# Netscape") and not content.startswith("# HTTP"):
                    content = "# Netscape HTTP Cookie File\n" + content

                cf.write_text(content.strip() + "\n", encoding="utf-8")
                return str(cf)
            except Exception as e:
                logger.warning(f"env_cookies yazılamadı: {e}")
    return None


class SesGuvenliPP(PostProcessor):
    """Birleştirilen videonun ses codec'ini kontrol eder; Opus ise AAC'ye çevirir."""
    def __init__(self, downloader=None, ffmpeg_dir=None):
        super().__init__(downloader)
        self.ffmpeg_dir = ffmpeg_dir

    def _bin(self, name: str) -> str:
        if self.ffmpeg_dir:
            p = Path(self.ffmpeg_dir) / (name + (".exe" if os.name == "nt" else ""))
            if p.exists():
                return str(p)
        return shutil.which(name) or name

    def run(self, info):
        dosya = info.get("filepath")
        if not dosya or not Path(dosya).exists() or Path(dosya).suffix.lower() != ".mp4":
            return [], info

        ffprobe = self._bin("ffprobe")
        ffmpeg = self._bin("ffmpeg")
        if not ffprobe or not ffmpeg:
            return [], info

        try:
            cikti = subprocess.run(
                [ffprobe, "-v", "error", "-select_streams", "a:0",
                 "-show_entries", "stream=codec_name", "-of", "json", str(dosya)],
                capture_output=True, text=True, timeout=30
            )
            codec = json.loads(cikti.stdout)["streams"][0]["codec_name"].lower()
            if codec in ("aac", "mp4a"):
                return [], info
            
            logger.info(f"Ses codec'i '{codec}' -> Tüm cihazlarla uyum için AAC'ye dönüştürülüyor...")
            gecici = Path(str(dosya) + ".audiofix.mp4")
            subprocess.run(
                [ffmpeg, "-y", "-i", str(dosya), "-c:v", "copy",
                 "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(gecici)],
                check=True, timeout=1800, capture_output=True
            )
            os.replace(gecici, dosya)
        except Exception as e:
            logger.warning(f"SesGuvenliPP atlandı veya hata verdi: {e}")

        return [], info


class DownloadRequest(BaseModel):
    url: str
    mode: str = "video"  # video, music, subtitle
    quality: Optional[str] = "best"  # best, 1080, 720, 480


class InfoRequest(BaseModel):
    url: str


def clean_old_files():
    """30 dakikadan eski geçici dosya ve klasörleri temizler."""
    now = time.time()
    try:
        for p in TEMP_DOWNLOAD_DIR.glob("*"):
            try:
                if (now - p.stat().st_mtime) > 1800:
                    if p.is_dir():
                        shutil.rmtree(p, ignore_errors=True)
                    elif p.is_file():
                        p.unlink(missing_ok=True)
            except Exception:
                pass
        # Eski tamamlanmış görevleri de hafızadan temizle
        to_del = [tid for tid, t in tasks.items() if now - t.get("created_at", now) > 3600]
        for tid in to_del:
            tasks.pop(tid, None)
    except Exception as e:
        logger.warning(f"Temizlik sırasında hata: {e}")


def _progress_hook_factory(task_id: str):
    def hook(d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            percent = (downloaded / total * 100) if total else 0
            speed = d.get("speed")
            speed_str = ""
            if speed:
                speed_str = f"{speed / 1048576:.1f} MB/s" if speed > 1048576 else f"{speed / 1024:.0f} KB/s"
            
            eta = d.get("eta")
            if task_id in tasks:
                tasks[task_id]["progress"] = round(min(percent, 99.0), 1)
                tasks[task_id]["speed"] = speed_str
                tasks[task_id]["eta"] = eta if eta is not None else 0
                tasks[task_id]["status"] = "downloading"
        elif d.get("status") == "finished":
            if task_id in tasks:
                tasks[task_id]["progress"] = 99.0
                tasks[task_id]["status"] = "processing"
                tasks[task_id]["speed"] = "Dönüştürülüyor..."
    return hook


def format_error_message(err: Exception) -> str:
    """Hata mesajlarını kullanıcı dostu, açıklayıcı Türkçe metinlere dönüştürür."""
    err_msg = str(err).lower().replace("’", "'").replace("`", "'")
    if "confirm your age" in err_msg or "age-restricted" in err_msg:
        return "Bu video yaş kısıtlamalı bir içeriktir."
    if "private" in err_msg:
        return "Bu video gizli veya erişime kapalı."
    if "members-only" in err_msg or "join this channel" in err_msg:
        return "Bu içerik yalnızca kanal üyelerine özeldir."
    if "unavailable" in err_msg or "does not exist" in err_msg or "not found" in err_msg:
        return "Video bulunamadı veya yayından kaldırılmış."
    if "copyright" in err_msg:
        return "Telif hakkı kısıtlaması nedeniyle video indirilemiyor."
    if "unsupported url" in err_msg or "is not a valid url" in err_msg:
        return "Desteklenmeyen veya geçersiz bir video linki girdiniz."
    if "geo" in err_msg or "country" in err_msg or "location" in err_msg:
        return "Bu içerik coğrafi bölge kısıtlaması nedeniyle indirilemiyor."
    if "altyazı bulunamadı" in err_msg or "no subtitles" in err_msg:
        return "Bu video için indirilebilir altyazı dosyası bulunamadı."
    if (
        "sign in to confirm" in err_msg
        or "not a bot" in err_msg
        or "confirm you are not a bot" in err_msg
        or "failed to extract any player response" in err_msg
        or "403" in err_msg
        or "forbidden" in err_msg
    ):
        return "YouTube bulut sunucusunu geçici olarak kısıtladı. Lütfen tekrar deneyin."
    
    # Teknik karmaşık hata mesajlarını temizle
    cleaned = re.sub(r'https?://\S+', '', str(err))
    cleaned = re.sub(r'ERROR:\s*(\[[^\]]+\])?', '', cleaned).strip()
    return f"İndirme başarısız: {cleaned[:140]}" if cleaned else "İndirme sırasında bir hata oluştu."


def _build_ydl_opts(
    mode: str,
    quality: str,
    task_dir: Path,
    ffmpeg_dir: Optional[str] = None,
    progress_hook = None,
    use_cookies: bool = False,
    player_clients: Optional[list] = None,
    override_format: Optional[str] = None
) -> Dict[str, Any]:
    """Video, müzik ve altyazı modları için standartlaştırılmış yt-dlp ayarlarını üretir."""
    cf = _get_cookiefile() if use_cookies else None
    
    # Varsayılan istemci: visionos (Bulut IP'lerinde bot korumasını ve 403 engellerini tamamen aşan Apple HLS/HTTPS motoru)
    clients = player_clients or ["visionos"]
    
    opts: Dict[str, Any] = {
        "outtmpl": str(task_dir / "%(title).100s [%(id)s].%(ext)s"),
        "noplaylist": True,
        "retries": 5,
        "fragment_retries": 5,
        "windowsfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "remote_components": ["ejs:github"],
        "extractor_args": {"youtube": {"player_client": clients}},
    }

    if shutil.which("node"):
        opts["js_runtimes"] = {"node": {}}

    if progress_hook:
        opts["progress_hooks"] = [progress_hook]

    if cf:
        opts["cookiefile"] = cf

    if ffmpeg_dir:
        opts["ffmpeg_location"] = ffmpeg_dir

    if override_format:
        opts["format"] = override_format
    elif mode == "video":
        if quality == "1080":
            fmt = (
                "bv*[height<=1080]+ba/b[height<=1080]/"
                "bv*[protocol^=m3u8][height<=1080]+ba*[protocol^=m3u8]/"
                "bestvideo[height<=1080]+bestaudio/"
                "best[height<=1080]/best"
            )
        elif quality == "720":
            fmt = (
                "bv*[height<=720]+ba/b[height<=720]/"
                "bv*[protocol^=m3u8][height<=720]+ba*[protocol^=m3u8]/"
                "bestvideo[height<=720]+bestaudio/"
                "best[height<=720]/best"
            )
        elif quality == "480":
            fmt = (
                "bv*[height<=480]+ba/b[height<=480]/"
                "bv*[protocol^=m3u8][height<=480]+ba*[protocol^=m3u8]/"
                "bestvideo[height<=480]+bestaudio/"
                "best[height<=480]/best"
            )
        else:
            fmt = (
                "bv*+ba/b/"
                "bv*[protocol^=m3u8]+ba*[protocol^=m3u8]/"
                "bestvideo*+bestaudio/best"
            )
        
        opts["format"] = fmt
        opts["merge_output_format"] = "mp4"
        opts["embed_metadata"] = True

    elif mode == "music":
        opts["format"] = "ba/b/best"
        opts["embed_metadata"] = True
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "0",  # 320 kbps
        }]

    elif mode == "subtitle":
        opts["skip_download"] = True
        opts["writesubtitles"] = True
        opts["writeautomaticsub"] = True
        opts["subtitleslangs"] = ["tr", "tr-orig", "en", "en-orig", "all"]
        opts["subtitlesformat"] = "srt/best"
        opts["postprocessors"] = [{
            "key": "FFmpegSubtitlesConvertor",
            "format": "srt",
        }]

    return opts


def _run_download_task(task_id: str, url: str, mode: str, quality: str):
    task = tasks[task_id]
    task["status"] = "starting"
    
    task_dir = TEMP_DOWNLOAD_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_dir = find_ffmpeg_path()
    
    # 4 Kademeli Otomatik Çözümleme Stratejisi
    cf = _get_cookiefile()
    strategies = [
        # 1. Aşama: Temiz VisionOS istemcisi (Çerezsiz, bot engeli olmayan direkt HLS/HTTPS akışı)
        {"name": "visionos_temiz", "use_cookies": False, "clients": ["visionos"], "format": None},
    ]
    if cf:
        # Eğer özel veya üye girişi gerekirse çerezli VisionOS
        strategies.append({"name": "visionos_cerezli", "use_cookies": True, "clients": ["visionos"], "format": None})
    # 2. Aşama: Android istemcisi (Google'ın yerel mobil CDN akışı - veri merkezi IP'lerine açık)
    strategies.append({"name": "android_mobil", "use_cookies": False, "clients": ["android"], "format": "ba/b/best"})
    # 3. Aşama: Android VR istemcisi
    strategies.append({"name": "android_vr", "use_cookies": False, "clients": ["android_vr"], "format": "best"})

    last_error = None
    title = "indirilen_dosya"
    files = []

    for strat in strategies:
        try:
            logger.info(f"[{task_id}] Deneniyor: {strat['name']}")
            opts = _build_ydl_opts(
                mode=mode,
                quality=quality,
                task_dir=task_dir,
                ffmpeg_dir=ffmpeg_dir,
                progress_hook=_progress_hook_factory(task_id),
                use_cookies=strat["use_cookies"],
                player_clients=strat["clients"],
                override_format=strat["format"]
            )
            with yt_dlp.YoutubeDL(opts) as ydl:
                if mode == "video":
                    ydl.add_post_processor(SesGuvenliPP(ydl, ffmpeg_dir))
                
                info = ydl.extract_info(url, download=True)
                title = (info or {}).get("title") or title

            files = [f for f in task_dir.rglob("*") if f.is_file() and not f.name.endswith(".part") and not f.name.endswith(".ytdl")]
            if files:
                last_error = None
                break
        except Exception as e:
            last_error = e
            err_lower = str(e).lower()
            logger.warning(f"[{task_id}] Strateji {strat['name']} hatası: {e}")
            if "copyright" in err_lower or "unavailable" in err_lower or "does not exist" in err_lower:
                break
            continue

    if last_error:
        readable_err = format_error_message(last_error)
        task["status"] = "error"
        task["error"] = readable_err
        logger.error(f"Görev hatası [{task_id}]: {readable_err} ({last_error})")
        try:
            shutil.rmtree(task_dir, ignore_errors=True)
        except Exception:
            pass
        return

    downloaded_file = max(files, key=lambda f: f.stat().st_size)
    file_size_bytes = downloaded_file.stat().st_size
    
    size_str = (
        f"{file_size_bytes / (1024 * 1024 * 1024):.2f} GB" if file_size_bytes > 1024 * 1024 * 1024 else
        f"{file_size_bytes / (1024 * 1024):.1f} MB" if file_size_bytes > 1024 * 1024 else
        f"{file_size_bytes / 1024:.0f} KB"
    )

    task["status"] = "completed"
    task["progress"] = 100.0
    task["speed"] = ""
    task["title"] = title
    task["file_path"] = str(downloaded_file)
    task["file_name"] = downloaded_file.name
    task["file_size"] = size_str
    logger.info(f"Görev tamamlandı [{task_id}]: {title} ({size_str})")


@app.get("/")
@app.get("/health")
def health_check():
    clean_old_files()
    ffmpeg_ready = find_ffmpeg_path() is not None or shutil.which("ffmpeg") is not None
    ytdlp_ver = getattr(getattr(yt_dlp, "version", None), "__version__", "bilinmiyor")
    cf = _get_cookiefile()
    cf_size = 0
    if cf and Path(cf).exists():
        try:
            cf_size = Path(cf).stat().st_size
        except Exception:
            pass
    return {
        "status": "ok",
        "service": "Downloader(+) API",
        "version": "1.3.0",
        "ffmpeg": "ready" if ffmpeg_ready else "missing",
        "has_cookies": cf is not None,
        "cookie_bytes": cf_size,
        "ytdlp_version": ytdlp_ver,
        "active_tasks": len([t for t in tasks.values() if t["status"] in ("starting", "downloading", "processing")])
    }


@app.post("/api/info")
async def get_video_info(req: InfoRequest):
    url = req.url.strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Geçerli bir URL giriniz.")

    def _extract():
        cf = _get_cookiefile()
        strategies = [
            {"use_cookies": False, "clients": ["visionos"]},
        ]
        if cf:
            strategies.append({"use_cookies": True, "clients": ["visionos"]})
        strategies.append({"use_cookies": False, "clients": ["android"]})
        strategies.append({"use_cookies": False, "clients": ["android_vr"]})

        last_e = None
        for strat in strategies:
            opts = {
                "skip_download": True,
                "quiet": True,
                "no_warnings": True,
                "retries": 3,
                "remote_components": ["ejs:github"],
                "extractor_args": {"youtube": {"player_client": strat["clients"]}},
            }
            if shutil.which("node"):
                opts["js_runtimes"] = {"node": {}}
            if strat["use_cookies"] and cf:
                opts["cookiefile"] = cf
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(url, download=False)
            except Exception as e:
                last_e = e
                continue
        if last_e:
            raise last_e
        raise RuntimeError("Video bilgisi alınamadı.")

    try:
        info = await asyncio.to_thread(_extract)
        duration = int(info.get("duration") or 0)
        minutes, seconds = divmod(duration, 60)
        dur_str = f"{minutes}:{seconds:02d}" if duration else ""
        
        return {
            "title": info.get("title", "Bilinmeyen Başlık"),
            "uploader": info.get("uploader") or info.get("channel") or "",
            "duration": dur_str,
            "thumbnail": info.get("thumbnail"),
            "view_count": info.get("view_count"),
        }
    except Exception as e:
        readable_err = format_error_message(e)
        logger.warning(f"Video bilgisi alınamadı [{url}]: {readable_err} ({e})")
        raise HTTPException(status_code=400, detail=f"Video bilgisi alınamadı: {readable_err}")


@app.get("/api/debug_info")
def debug_info(url: str = "https://youtu.be/AOCdTASFoc4"):
    import traceback
    results = []
    cf = _get_cookiefile()
    strategies = [
        {"name": "visionos", "use_cookies": False, "clients": ["visionos"]},
        {"name": "android", "use_cookies": False, "clients": ["android"]},
        {"name": "android_vr", "use_cookies": False, "clients": ["android_vr"]},
        {"name": "tv", "use_cookies": False, "clients": ["tv"]},
        {"name": "mweb", "use_cookies": False, "clients": ["mweb"]},
    ]
    if cf:
        strategies.insert(0, {"name": "visionos_cerezli", "use_cookies": True, "clients": ["visionos"]})
    for strat in strategies:
        opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": strat["clients"]}},
        }
        if strat.get("use_cookies") and cf:
            opts["cookiefile"] = cf
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                results.append({"strat": strat["name"], "success": True, "title": info.get("title")})
                break
        except Exception as e:
            results.append({"strat": strat["name"], "success": False, "error": str(e), "tb": traceback.format_exc()[-300:]})
    return {"results": results, "cookiefile_found": cf, "has_node": shutil.which("node") is not None}


@app.post("/api/download")
async def start_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    url = req.url.strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Geçerli bir URL giriniz.")

    mode = req.mode.lower()
    if mode not in ("video", "music", "subtitle"):
        raise HTTPException(status_code=400, detail="Geçersiz indirme modu.")

    clean_old_files()
    task_id = str(uuid.uuid4())[:8]
    
    tasks[task_id] = {
        "id": task_id,
        "url": url,
        "mode": mode,
        "quality": req.quality or "best",
        "status": "queued",
        "progress": 0.0,
        "speed": "",
        "eta": 0,
        "title": "Hazırlanıyor...",
        "file_path": None,
        "file_name": None,
        "file_size": "",
        "error": None,
        "created_at": time.time(),
    }

    # İndirme işlemini arka plan thread havuzunda başlat
    executor.submit(_run_download_task, task_id, url, mode, req.quality or "best")
    
    return {"task_id": task_id, "status": "queued"}


@app.get("/api/status/{task_id}")
def check_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")
    return task


@app.get("/api/file/{task_id}")
def download_file(task_id: str, background_tasks: BackgroundTasks):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")
    
    if task["status"] != "completed" or not task.get("file_path"):
        raise HTTPException(status_code=400, detail="Dosya henüz hazır değil veya indirme başarısız.")

    file_path = Path(task["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dosya sunucuda bulunamadı.")

    media_type = (
        "video/mp4" if file_path.suffix.lower() == ".mp4" else
        "audio/mpeg" if file_path.suffix.lower() == ".mp3" else
        "application/x-subrip" if file_path.suffix.lower() == ".srt" else
        "application/octet-stream"
    )

    filename = task.get("file_name") or file_path.name
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.on_event("startup")
async def startup_event():
    """Sunucu başladığında her 5 dakikada bir disk temizliği yapan arka plan görevini başlatır."""
    async def periodic_cleaner():
        while True:
            await asyncio.sleep(300)
            try:
                clean_old_files()
            except Exception as e:
                logger.warning(f"Periyodik temizlik hatası: {e}")

    asyncio.create_task(periodic_cleaner())


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print("=" * 60)
    print(f"  Downloader(+) API Başlatılıyor: http://127.0.0.1:{port}")
    print("=" * 60)
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
