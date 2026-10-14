# Gelecek Versiyonlar — Fikir ve Rapor Dosyası

> Bu dosya, Freebuff İndirici'nin (video/müzik/altyazı indirici) mevcut durumunu,
> eksiklerini ve gelecekte yapılabilecek geliştirmeleri saklamak için tutulur.
> Tarih: 17 Ağustos 2026

---

## A) Mevcut Durum (özet)

- **video.bat / muzik.bat / altyazi.bat** + **ortak.bat** (Python kurulumu) + **indirici.py** (ana motor)
- Sıralı kuyruk: birden fazla link sırayla iner, indirme sürerken yeni link eklenebilir
- İndirme hızı/ilerleme göstergesi (yt-dlp)
- Yaş sınırlı videoları otomatik atlama
- İnternet koparsa yarım kalan iş iptal edilir (sürdürülmez)
- Otomatik kurulum: yt-dlp (global Python) + ffmpeg (`araçlar/ffmpeg`)
- Altyazı modu: TR+EN, srt dönüşümü; bir dil alınamazsa yedek dille otomatik deneme
- MP3 dönüşümü (320 kbps) ve MP4 birleştirme (en yüksek kalite)

---

## B) Eksikler / Zayıf Noktalar (önem sırasına göre)

1. **Çerez (giriş) desteği yok**
   - Yaş sınırı, üyeliğe özel videolar, bölgesel kısıtlamalar ancak tarayıcı çereziyle çözülür.
   - Şu an yaş sınırlı videolar "atlanıyor" — hesap girişi istersek çerez desteği şart.
2. **Log kaydı yok**
   - Hata olursa mesajı ekrandan kopyalamak gerekiyor; kalıcı `log.txt` yazılsa iyi olur.
3. **Kalite sınırı yok**
   - 4K/8K videolar 5-20 GB olabilir. Kullanıcı onayına göre 1080p sınırı eklenebilir.
4. **Playlist desteği yok**
   - Bilinçli tercih (tek tek link atılacak). İstenirse sonra eklenir.
5. **Altyazı dili sabit (TR+EN)**
   - "Tüm diller" seçeneği istenirse eklenir.
6. **Disk alanı kontrolü yok**
   - Dolan diskte indirme yarıda hata verir; önceden uyarı iyi olur.
7. **İndirme bitince bildirim yok**
   - Windows bildirimi veya ses eklense kullanıcı pencerede beklemek zorunda kalmaz.
8. **Uyku modu riski**
   - Büyük indirme sırasında bilgisayar uykuya geçerse iş kesilir.
   - Kullanıcıya "uykuya geçmeyi kapat" notu verilmeli.
9. **Codec uyumluluğu (ÖNEMLİ — ÇÖZÜLDÜ, 17.08.2026)**
   - Sorun: "en iyi" ses formatı genelde Opus (251) seçiliyordu; Opus, MP4 kapsayıcısında birçok
     oynatıcıda (Windows varsayılan oynatıcı, bazı TV'ler) ses vermiyordu — video oynuyor, ses çıkmıyordu.
   - Çözüm 1: Ses formatı öncelikle m4a (AAC) seçilecek şekilde format filtresi eklendi
     (`bestvideo*+bestaudio[ext=m4a]/...`) — çoğu videoda yeniden kodlamaya gerek kalmadan AAC gelir.
   - Çözüm 2: Yine de Opus gelirse (nadir videolar) `SesGuvenliPP` son işlemi sesi otomatik
     AAC'ye çevirir (video aynen korunur).
   - Doğrulandı: hem m4a seçimi hem Opus→AAC dönüşümü gerçek indirmeyle test edildi, sonuç AAC.
10. **HDR / AV1 uyumluluğu**
    - En iyi format bazen HDR veya AV1 seçer; eski oynatıcılarda sorun çıkabilir.
    - İstenirse H264'e sabitlenebilir.

---

## C) Fazlalıklar / Sadeleştirilebilecekler

- `araçlar/ffmpeg` ~200 MB yer kaplıyor — ama ilk çalıştırmayı anında yapıyor; değerine değer.
- MP3'lere otomatik etiket (başlık/sanatçı) yazılıyor — küçük bonus.
- Genel olarak kod sade; ciddi bir "fazlalık" yok.

---

## D) Gelecekte Yapılabilecekler (fikir listesi)

1. **Çerez desteği** — en değerli: tarayıcıdan otomatik çerez alıp hesabıyla indirme.
2. **Basit web arayüzü** — bilgisayarda küçük bir sayfa; linkler oraya yapıştırılır,
   telefonda açılıp telefondan yönetilebilir (konsol yerine).
3. **Playlist / kanal toplu indirme** — tek linkle tüm liste.
4. **İndirme bitince bildirim** — Windows balonu veya ses.
5. **Kalite menüsü** — her indirmede "1080p mi 4K mı?" sorusu.
6. **Bant genişliği sınırlama** — interneti yormadan indirme.
7. **Otomatik klasör düzenleme** — kanal adına göre alt klasörler.
8. **Kuyruk kaydetme** — uygulama kapansa bile bekleyen liste kalsın
   (yarım iş yine iptal, sadece bekleyenler kaydedilir).
9. **Şifreli video desteği** — URL'ye gömülü şifreli videolar.
10. **İstatistik** — indirilen dosya sayısı, toplam boyut, hız geçmişi.

---

## E) Test Kontrol Listesi (kullanıcı testi için)

- İlk link → hız göstergesi ve ilerleme çubuğu görünmeli.
- İkinci link indirme sürerken yapıştırılmalı → "Sırada bekleyen 1 link var" demeli,
  biri bitince otomatik başlamalı.
- Aynı anda 2-3 link boşlukla yapıştırılmalı → sırayla inmeli.
- Altyazı modunda TR altyazısı olmayan video → EN ile devam etmeli.
- Hata olursa ekrandaki mesaj aynen paylaşılmalı.

---

## F) Not

- İndirilen videoda ses olmaması sorunu (Opus codec) 17.08.2026'da tespit edilip düzeltildi.
- Kod değişiklikleri manuel; gelecekte otomatik güncelleme mekanizması (örn. GitHub) düşünülebilir.
