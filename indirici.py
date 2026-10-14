# -*- coding: utf-8 -*-
"""
Freebuff İndirici — yt-dlp tabanlı video / müzik / altyazı indirme aracı.

Kullanım:
    python indirici.py video      -> MP4, en yüksek kalite  -> "indirilen video" klasörü
    python indirici.py muzik      -> MP3, en yüksek kalite  -> "indirilen müzik" klasörü
    python indirici.py altyazi    -> sadece altyazı (srt)   -> "indirilen altyazı" klasörü

Özellikler:
- Linkleri sıraya alır, bir indirme bitince sıradakine geçer.
- İndirme sürerken yeni link yapıştırılabilir (sıraya eklenir).
- İnternet koparsa yarım kalan iş iptal edilir (sürdürülmez, baştan başlar).
- Yaş sınırlı videolar otomatik atlanır.
- İlk çalıştırmada yt-dlp ve ffmpeg otomatik kurulur.
"""

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

# ---------------------------------------------------------------
# AYARLAR — ihtiyacın olursa buradan değiştirebilirsin
# ---------------------------------------------------------------
ALTYAZI_DILLERI = ["tr", "en"]        # altyazı modunda indirilecek diller
MP3_KALITE = "0"                      # 0 = en iyi (320 kbps)
# En yüksek video kalitesi + ses öncelikle m4a (AAC):
# Opus ses, MP4 içinde çoğu oynatıcıda ses vermez (video oynar, ses çıkmaz).
VIDEO_FORMAT = "bestvideo*+bestaudio[ext=m4a]/bestvideo*+bestaudio/best"
RETRY_SAYISI = 3                      # ağ hatasında yeniden deneme sayısı
# ---------------------------------------------------------------

MODE_VIDEO = "video"
MODE_MUZIK = "muzik"
MODE_ALTYAZI = "altyazi"

BASE_DIR = Path(__file__).resolve().parent
ARACLAR = BASE_DIR / "araçlar"        # ffmpeg buraya iner (otomatik)

KLASORLER = {
    MODE_VIDEO: BASE_DIR / "indirilen video",
    MODE_MUZIK: BASE_DIR / "indirilen müzik",
    MODE_ALTYAZI: BASE_DIR / "indirilen altyazı",
}

MOD_BASLIK = {
    MODE_VIDEO: "VIDEO İndirici (MP4 — en yüksek kalite)",
    MODE_MUZIK: "MÜZİK İndirici (MP3 — en yüksek kalite)",
    MODE_ALTYAZI: "ALTYAZI İndirici (sadece altyazı)",
}


def banner(mode):
    print("=" * 58)
    print("  " + MOD_BASLIK[mode])
    print("  İndirme klasörü: " + str(KLASORLER[mode]))
    print("=" * 58)
    print("Birden fazla linki aynı anda yapıştırabilirsiniz (boşluk veya virgülle ayırın).")
    print("İndirme sürerken yeni link yapıştırırsanız sıraya girer, sırayla iner.")
    print("Çıkmak için: q  |  Anında iptal için: Ctrl+C")
    print()


# ---------------------------------------------------------------
# Kurulum: yt-dlp ve ffmpeg
# ---------------------------------------------------------------

def ytdlp_hazirla():
    try:
        import yt_dlp  # noqa: F401
        # yt-dlp'yi güncel tut (YouTube sık sık kırıyor). Olmazsa sorun değil,
        # kurulu sürümle devam edilir.
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "--quiet", "yt-dlp"],
                timeout=120, check=False,
            )
        except Exception:
            pass
    except ImportError:
        print("yt-dlp kuruluyor (ilk çalıştırmada bir kez, internet gerekli)...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"], check=True)
        except subprocess.CalledProcessError:
            # Bazı sistemlerde varsayılan pip indeksi çalışmaz; resmi indeksi dene
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "-i", "https://pypi.org/simple", "yt-dlp"],
                check=True,
            )


def ffmpeg_var_mi():
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


FFMPEG_KAYNAKLARI = [
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
]


def _ffmpeg_parcasi_indir(zip_yolu, url, baslangic):
    """Tek kaynaktan indirir; sunucu izin veriyorsa kaldığı byte'tan devam eder."""
    basliklar = {"User-Agent": "Mozilla/5.0"}
    if baslangic:
        basliklar["Range"] = f"bytes={baslangic}-"
    istek = urllib.request.Request(url, headers=basliklar)
    with urllib.request.urlopen(istek, timeout=30) as yanit:
        kismi = yanit.status == 206 and baslangic
        gercek_baslangic = baslangic if kismi else 0
        toplam = int(yanit.headers.get("Content-Length") or 0) + gercek_baslangic
        alinan = gercek_baslangic
        mod = "ab" if kismi else "wb"
        with open(zip_yolu, mod) as f:
            while True:
                parca = yanit.read(1024 * 1024)
                if not parca:
                    break
                f.write(parca)
                alinan += len(parca)
                yuzde = (alinan / toplam * 100) if toplam else 0
                print(f"\r  %5.1f%%  ({alinan / 1048576:.1f} MB)" % yuzde, end="", flush=True)
    return alinan


def ffmpeg_indir():
    """ffmpeg'i yerel araçlar klasörüne indirir (bir kez). Çoklu kaynak + devam desteği."""
    hedef = ARACLAR / "ffmpeg"
    hedef.mkdir(parents=True, exist_ok=True)
    if (hedef / "ffmpeg.exe").exists() and (hedef / "ffprobe.exe").exists():
        return hedef
    if (hedef / "ffmpeg").exists() and (hedef / "ffprobe").exists():
        return hedef

    zip_yolu = ARACLAR / "ffmpeg.zip"
    print("FFmpeg indiriliyor (ilk çalıştırmada bir kez, yaklaşık 100 MB)...")
    print("İnternet yavaşsa birkaç dakika sürebilir; yarıda kalırsa tekrar deneyin,")
    print("indirme kaldığı yerden devam eder.")
    son_hata = None
    ilk_kaynak = True
    for url in FFMPEG_KAYNAKLARI:
        kaynak_ad = url.split("/")[2]
        if not ilk_kaynak:
            # farklı kaynağa geçerken eski yarım dosyayı temizle
            try:
                zip_yolu.unlink(missing_ok=True)
            except Exception:
                pass
        ilk_kaynak = False
        for deneme in range(3):
            try:
                baslangic = zip_yolu.stat().st_size if zip_yolu.exists() else 0
                _ffmpeg_parcasi_indir(zip_yolu, url, baslangic)
            except Exception as e:
                son_hata = e
                print(f"\n  ({kaynak_ad}, deneme {deneme + 1}: {type(e).__name__} — kaldığı yerden devam edilecek)")
                time.sleep(3)
                continue
            # İndirme bitti — zip'i doğrula ve çıkar
            try:
                with zipfile.ZipFile(zip_yolu) as z:
                    ffmpeg_uzantili = ffprobe_uzantili = None
                    for isim in z.namelist():
                        if isim.endswith("/bin/ffmpeg.exe") and ffmpeg_uzantili is None:
                            ffmpeg_uzantili = isim
                        elif isim.endswith("/bin/ffprobe.exe") and ffprobe_uzantili is None:
                            ffprobe_uzantili = isim
                    if not ffmpeg_uzantili or not ffprobe_uzantili:
                        raise RuntimeError("ffmpeg zip içeriği tanınamadı")
                    with z.open(ffmpeg_uzantili) as kaynak, open(hedef / "ffmpeg.exe", "wb") as cikti:
                        shutil.copyfileobj(kaynak, cikti)
                    with z.open(ffprobe_uzantili) as kaynak, open(hedef / "ffprobe.exe", "wb") as cikti:
                        shutil.copyfileobj(kaynak, cikti)
            except Exception as e:
                son_hata = e
                print(f"\n  ({kaynak_ad}: indirilen dosya bozuk — baştan deneniyor)")
                try:
                    zip_yolu.unlink(missing_ok=True)
                except Exception:
                    pass
                time.sleep(3)
                continue
            print("\nFFmpeg hazır.")
            try:
                zip_yolu.unlink(missing_ok=True)
            except Exception:
                pass
            return hedef
    print(f"\nFFmpeg indirilemedi: {son_hata}")
    print("Manuel çözüm: https://www.gyan.dev/ffmpeg/builds/ adresinden 'release")
    print("essentials' zip'ini indirip içindeki bin klasöründeki ffmpeg.exe ve")
    print("ffprobe.exe dosyalarını bu klasördeki 'araçlar\\ffmpeg' içine koyun.")
    return None


# ---------------------------------------------------------------
# İndirme
# ---------------------------------------------------------------

def secenekler(mode, ffmpeg_konum, diller=None):
    klasor = KLASORLER[mode]
    klasor.mkdir(parents=True, exist_ok=True)
    sec = {
        "outtmpl": str(klasor / "%(title)s [%(id)s].%(ext)s"),
        "noplaylist": True,          # tek video indirir, oynatma listesi indirmez
        "continue_dl": False,        # yarım kalan indirme sürdürülmez, baştan başlar
        "continuedl": False,         # (aynı ayar, farklı sürümler için güvence)
        "retries": RETRY_SAYISI,
        "fragment_retries": RETRY_SAYISI + 2,
        "windowsfilenames": True,
    }
    if ffmpeg_konum:
        sec["ffmpeg_location"] = str(ffmpeg_konum)

    ffmpeg_hazir = bool(ffmpeg_konum) or ffmpeg_var_mi()
    if mode == MODE_VIDEO:
        sec["format"] = VIDEO_FORMAT
        sec["merge_output_format"] = "mp4"
        if ffmpeg_hazir:
            sec["embed_metadata"] = True
    elif mode == MODE_MUZIK:
        sec["format"] = "bestaudio/best"
        if ffmpeg_hazir:
            sec["embed_metadata"] = True
        sec["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": MP3_KALITE,
        }]
    elif mode == MODE_ALTYAZI:
        sec["skip_download"] = True
        sec["writesubtitles"] = True
        sec["writeautomaticsub"] = True
        sec["subtitleslangs"] = list(diller or ALTYAZI_DILLERI)
        sec["subtitlesformat"] = "srt/best"
        # vtt -> srt dönüşümü (ffmpeg gerekir)
        sec["postprocessors"] = [{
            "key": "FFmpegSubtitlesConvertor",
            "format": "srt",
        }]
    return sec


def gecici_dosyalari_temizle(klasor):
    """Yarım kalan indirme kalıntılarını (parça dosyaları) siler."""
    for desen in ("*.part", "*.ytdl", "*.temp"):
        for dosya in klasor.glob(desen):
            try:
                dosya.unlink()
            except OSError:
                pass


def linki_indir(url, mode, ffmpeg_konum, diller=None):
    import yt_dlp

    if mode == MODE_MUZIK and not (ffmpeg_konum or ffmpeg_var_mi()):
        print("✖ MP3 dönüşümü için FFmpeg gerekli ama kurulamadı.")
        print("  (İnternet bağlantınızı kontrol edip tekrar deneyin.)")
        return "hata"

    klasor = KLASORLER[mode]
    sec = secenekler(mode, ffmpeg_konum, diller)
    print(f"\n>>> İndiriliyor: {url}")
    from yt_dlp.postprocessor import PostProcessor

    class SesGuvenliPP(PostProcessor):
        """Birleştirilen videonun sesinin her oynatıcıda çalışmasını garanti eder:
        ses codec'i AAC değilse (örn. Opus) videoyu aynen koruyup sesi AAC'ye çevirir."""

        def __init__(self, downloader=None, ffmpeg_konum=None):
            super().__init__(downloader)
            self.ffmpeg_konum = ffmpeg_konum

        def run(self, info):
            dosya = info.get("filepath")
            if not dosya or not Path(dosya).exists():
                return [], info
            if Path(dosya).suffix.lower() != ".mp4":
                return [], info
            ffprobe = self._biner("ffprobe")
            ffmpeg = self._biner("ffmpeg")
            if not ffprobe or not ffmpeg:
                return [], info
            cikti = subprocess.run(
                [str(ffprobe), "-v", "error", "-select_streams", "a:0",
                 "-show_entries", "stream=codec_name", "-of", "json", str(dosya)],
                capture_output=True, text=True, timeout=60,
            )
            try:
                codec = json.loads(cikti.stdout)["streams"][0]["codec_name"]
            except Exception:
                return [], info  # ses yok veya okunamadı — dokunma
            if codec.lower() in ("aac", "mp4a"):
                return [], info
            self.to_screen(f"Ses codec'i '{codec}' — her oynatıcıda çalışması için AAC'ye çevriliyor...")
            gecici = Path(str(dosya) + ".sesduzeltme.mp4")
            subprocess.run(
                [str(ffmpeg), "-y", "-i", str(dosya), "-c:v", "copy",
                 "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(gecici)],
                check=True, timeout=3600, capture_output=True,
            )
            os.replace(gecici, dosya)
            return [], info

        def _biner(self, ad):
            if self.ffmpeg_konum:
                p = Path(self.ffmpeg_konum) / (ad + (".exe" if os.name == "nt" else ""))
                if p.exists():
                    return p
            return shutil.which(ad)

    try:
        with yt_dlp.YoutubeDL(sec) as ydl:
            if mode == MODE_VIDEO:
                ydl.add_post_processor(SesGuvenliPP(ydl, ffmpeg_konum))
            bilgi = ydl.extract_info(url, download=True)
        baslik = (bilgi or {}).get("title") or url
        print(f"✔ Tamamlandı: {baslik}")
        return "ok"
    except yt_dlp.utils.DownloadError as hata:
        mesaj = str(hata)
        mesaj_kucuk = mesaj.lower()
        # Altyazı modu: bir dil alınamadıysa (örn. geçici YouTube sınırlaması)
        # o dili atlayıp kalan dillerle bir kez daha dene
        if mode == MODE_ALTYAZI and diller is None and "for '" in mesaj:
            eslesme = re.search(r"for '([^']+)'", mesaj)
            if eslesme:
                kalan = [d for d in ALTYAZI_DILLERI if d != eslesme.group(1)]
                if kalan:
                    print(f"  '{eslesme.group(1)}' altyazısı alınamadı (YouTube sınırlaması olabilir).")
                    print(f"  Kalan dillerle ({', '.join(kalan)}) tekrar deneniyor...")
                    gecici_dosyalari_temizle(klasor)
                    time.sleep(5)
                    return linki_indir(url, mode, ffmpeg_konum, diller=kalan)
        if any(a in mesaj_kucuk for a in ("age", "confirm your age", "sign in", "yaş")):
            print("⛔ Bu video yaş sınırlı olduğu için atlandı.")
        elif "ffmpeg" in mesaj_kucuk and "not installed" in mesaj_kucuk:
            print("✖ FFmpeg kurulamadığı için bu işlem yapılamadı.")
            print("  (İnternet bağlantınızı kontrol edip tekrar deneyin.)")
        elif "playlist" in mesaj_kucuk and "yes-playlist" in mesaj_kucuk:
            print("⛔ Bu bir oynatma listesi (playlist) linki. Bu araç tek videoları indirir.")
        else:
            print(f"✖ İndirme başarısız: {mesaj}")
            print("  Olası nedenler: internet kopukluğu, hatalı link, silinmiş video,")
            print("  bölgesel kısıtlama veya yaş sınırı.")
        gecici_dosyalari_temizle(klasor)
        return "hata"
    except KeyboardInterrupt:
        print("\n⛔ İndirme iptal edildi (Ctrl+C).")
        gecici_dosyalari_temizle(klasor)
        return "iptal"


# ---------------------------------------------------------------
# Ana döngü: kuyruk + klavye girişi
# ---------------------------------------------------------------

def ana(mode):
    # Türkçe karakterler ve semboller her ortamda düzgün bassın:
    # (konsolda zaten UTF-8 kullanılır; yönlendirilmiş çıktıda çökmeyi önler)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    banner(mode)
    print("Bağımlılıklar kontrol ediliyor...")
    ytdlp_hazirla()

    # Altyazı modu da srt dönüşümü için ffmpeg ister; hepsi için garanti et
    ffmpeg_konum = None
    if ffmpeg_var_mi():
        print("FFmpeg hazır (sistemde kurulu).")
    else:
        ffmpeg_konum = ffmpeg_indir()
    print()

    kuyruk = queue.Queue()

    def okuyucu():
        """Klavyeden link okur ve kuyruğa ekler (indirme sürerken de çalışır)."""
        while True:
            try:
                satir = input("Link girin (birden fazla: boşluk/virgül; çıkış: q) > ")
            except (EOFError, KeyboardInterrupt):
                kuyruk.put(("kapat", ""))
                return
            girdiler = [p for p in satir.replace(",", " ").split() if p.strip()]
            for g in girdiler:
                g = g.strip().strip('"').strip("'")
                if g.lower() in ("q", "çık", "çıkış", "exit", "quit"):
                    kuyruk.put(("kapat", ""))
                elif g.lower().startswith("http"):
                    kuyruk.put(("link", g))
                else:
                    print(f"  Geçersiz giriş atlandı: {g}")

    threading.Thread(target=okuyucu, daemon=True).start()

    print("Hazır! Linkleri yapıştırın.")
    while True:
        tur, deger = kuyruk.get()
        if tur == "kapat":
            print("\nKapatılıyor...")
            break
        sonuc = linki_indir(deger, mode, ffmpeg_konum)
        if sonuc == "iptal":
            break
        bekleyen = sum(1 for i in list(kuyruk.queue) if i[0] == "link")
        if bekleyen:
            print(f"\nSırada bekleyen {bekleyen} link var.")
            # YouTube hız sınırına (429) takılmamak için indirmeler arasında kısa bekleme
            time.sleep(3)
        else:
            print("\nSıra boş. Yeni link yapıştırabilir veya 'q' yazıp çıkabilirsiniz.")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in KLASORLER:
        print("Kullanım: python indirici.py video | muzik | altyazi")
        sys.exit(1)
    try:
        ana(sys.argv[1])
    except KeyboardInterrupt:
        print("\nKapatılıyor...")
    except Exception as e:
        print(f"\nBeklenmeyen hata: {e}")
        input("\nKapatmak için Enter'a basın...")
