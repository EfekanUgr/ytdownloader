import os
import re
import sys
import time
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
CONFIG_JS = ROOT_DIR / "dist" / "config.js"

def find_cloudflared():
    for p in ROOT_DIR.rglob("cloudflared.exe"):
        if p.is_file():
            return str(p.resolve())
    return None

def main():
    print("=" * 60)
    print(" Downloader(+) Ev Koprusu Baslatiliyor...")
    print("=" * 60)

    cloudflared_bin = find_cloudflared()
    if not cloudflared_bin:
        print("[!] cloudflared.exe bulunamadi!")
        sys.exit(1)
    print(f"[*] Cloudflared ikilisi: {cloudflared_bin}")

    # 1. Yerel API kontrolu / baslatma
    import socket
    def port_open(p=8000):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', p)) == 0

    if not port_open(8000):
        print("[1] Yerel FastAPI sunucusu baslatiliyor (Port 8000)...")
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(2)
    else:
        print("[1] Port 8000 aktif.")

    # 2. Cloudflare Tunelini baslat
    print("[2] Cloudflare Tuneli baslatiliyor...")
    tunnel_proc = subprocess.Popen(
        [cloudflared_bin, "tunnel", "--url", "http://127.0.0.1:8000"],
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace"
    )

    tunnel_url = None
    start = time.time()
    while time.time() - start < 30:
        line = tunnel_proc.stderr.readline()
        if not line:
            time.sleep(0.1)
            continue
        m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if m:
            tunnel_url = m.group(0)
            break

    if not tunnel_url:
        print("[!] Tunel URL'si alinamadi.")
        sys.exit(1)

    print(f"\n>>> AKTIF KOPRU ADRESI: {tunnel_url} <<<\n")

    # 3. dist/config.js dosyasini guncelle
    config_content = f"""// Downloader(+) Yapilandirmasi
window.CONFIG = {{
  DEFAULT_API_URL: "{tunnel_url}",
  RENDER_API_URL: "https://ytdownloader-p8pr.onrender.com"
}};
"""
    CONFIG_JS.write_text(config_content, encoding="utf-8")
    print(f"[3] dist/config.js guncellendi ({tunnel_url})")

    # 4. Git commit & push yaparak Netlify'a yayinla
    try:
        print("[4] Netlify icin GitHub'a pushlaniyor...")
        subprocess.run(["git", "add", "dist/config.js"], cwd=str(ROOT_DIR), check=True)
        subprocess.run(["git", "commit", "-m", f"chore: update active home bridge url to {tunnel_url}"], cwd=str(ROOT_DIR), check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=str(ROOT_DIR), check=True)
        print("[OK] Netlify'a basariyla gonderildi! ~15 saniye icinde telefonda hazir.")
    except Exception as e:
        print(f"[!] Git guncelleme hatasi: {e}")

    print("\n" + "=" * 60)
    print(" SISTEM TAMAMEN DEVREDE!")
    print(f" Web Sitesi: https://ytindirici.netlify.app")
    print(f" Ev Koprusu: {tunnel_url}")
    print("=" * 60 + "\n")

    # Tunel surecini canli tut
    try:
        while True:
            time.sleep(1)
            if tunnel_proc.poll() is not None:
                print("[!] Tunel kapandi!")
                break
    except KeyboardInterrupt:
        tunnel_proc.terminate()

if __name__ == "__main__":
    main()
