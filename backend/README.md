# Downloader(+) — Backend API

Bu klasör, Netlify'da yayınlanan web arayüzünüzün video ve müzik indirmesini sağlayan FastAPI tabanlı Python sunucusudur.

---

## 🚀 1. Ücretsiz Canlıya Alma (Render.com ile — Tavsiye Edilen)

Render.com, Docker tabanlı uygulamaları ve FFmpeg'i ücretsiz olarak 7/24 çalıştırır.

1. **GitHub'a Yükleyin:**
   - Bu `backend` klasörünü (veya tüm projeyi) GitHub hesabınızda bir repository olarak oluşturun ve yükleyin.
2. **Render.com'a Girin:**
   - [render.com](https://render.com) adresine gidip ücretsiz üye olun.
   - **New +** butonuna basıp **Web Service** seçin.
   - GitHub deponuzu bağlayın.
   - **Environment:** `Docker` seçin (Dockerfile otomatik algılanacaktır).
   - **Instance Type:** `Free` seçin.
   - **Create Web Service** butonuna tıklayın.
3. **URL'inizi Alın:**
   - Render 2-3 dakika içinde kurulumu tamamlar ve size `https://ornek-servis.onrender.com` gibi bir adres verir.
4. **Netlify Sitenize Bağlayın:**
   - Netlify'daki sitenize girin, sağ üstteki ⚙ Ayarlar simgesine tıklayın.
   - Render'dan aldığınız adresi yapıştırıp **Kaydet** butonuna basın. (Veya `dist/config.js` içine yazıp tekrar deploy edebilirsiniz).
   - Artık siteniz tüm dünyaya açık ve indirme yapmaya hazır!

---

## 💻 2. Bilgisayarınızda Yerel Olarak Çalıştırma

Geliştirme yaparken veya kendi bilgisayarınızdan test etmek için:
- `start.bat` dosyasına çift tıklayın.
- Sunucu `http://127.0.0.1:8000` adresinde açılacaktır.
