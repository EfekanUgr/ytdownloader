# -*- coding: utf-8 -*-
"""
Downloader(+) Ev Sunucusu ve Cloudflare Tünel Köprüsü
Ev internetiniz üzerinden çalışan yerel API'yi güvenli bir HTTPS adresiyle dış dünyaya açar.
Böylece YouTube veri merkezi IP bloklarına asla takılmazsınız.
"""

import os
import re
import sys
import time
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
CLOUDFLARED = ROOT_DIR / "araçlar" / "cloudflared.exe"

def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("\n" + "=" * 65)
    print("   Downloader(+) - Ev Interneti Destekli Web Sunucusu")
    print("=" * 65 + "\n")

    if not CLOUDFLARED.exists():
        print(f"HATA: {CLOUDFLARED} bulunamadi!")
        input("\nCikmak icin Enter'a basin...")
        return

    import socket
    def port_open(p=8000):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', p)) == 0

    server_proc = None
    if not port_open(8000):
        print("[1/2] Yerel API baslatiliyor (Port 8000)...")
        server_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1)
    else:
        print("[1/2] Yerel API zaten Port 8000 uzerinde calisiyor.")

    # 2. Cloudflare Tünelini Başlat
    print("[2/2] Guvenli Cloudflare HTTPS tuneli aciliyor...")
    tunnel_cmd = [str(CLOUDFLARED), "tunnel", "--url", "http://127.0.0.1:8000"]
    tunnel_proc = subprocess.Popen(
        tunnel_cmd,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace"
    )

    tunnel_url = None
    start_time = time.time()

    # Tünel linkini loglardan yakala
    while time.time() - start_time < 20:
        line = tunnel_proc.stderr.readline()
        if not line:
            time.sleep(0.1)
            continue
        
        match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if match:
            tunnel_url = match.group(0)
            break

    if not tunnel_url:
        print("[!] Tunel linki olusturulamadi. Internet baglantinizi kontrol edin.")
        server_proc.terminate()
        tunnel_proc.terminate()
        input("\nCikmak icin Enter'a basin...")
        return

    # Başarılı - Kullanıcıya Şık Ekran Göster
    print("\n" + "=" * 65)
    print("  [OK] TEBRIKLER! EV INTERNETI KOPRUNUZ CANLI YAYINDA!")
    print("=" * 65)
    print(f"\n  SENIN CANLI API LINKIN:\n  >>> {tunnel_url} <<<\n")
    print("-" * 65)
    print("  NASIL KULLANACAKSIN?")
    print("  1. Disaridayken telefonundan https://ytindirici.netlify.app adresini ac.")
    print(f"  2. Yukaridaki {tunnel_url} adresini kopyalayip")
    print("     sitedeki 'API Baglantisi' kutusuna yapistir ve Baglan'a bas.")
    print("  3. Artik hicbir video bot engeline takilmayacak! Tum indirmeler")
    print("     evindeki PC ve ev internetin uzerinden aninda telefonuna inecek.")
    print("-" * 65)
    print("  (Bu pencere acik kaldigi surece kopru aktif kalir.)")
    print("  (Kapatmak icin pencereyi carpisindan kapatabilirsiniz.)\n")

    try:
        tunnel_proc.wait()
    except KeyboardInterrupt:
        print("\nSunucu kapatılıyor...")
    finally:
        if server_proc:
            try:
                server_proc.terminate()
            except Exception:
                pass
        try:
            tunnel_proc.terminate()
        except Exception:
            pass

if __name__ == "__main__":
    main()
