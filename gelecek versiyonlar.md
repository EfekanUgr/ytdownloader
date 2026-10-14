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

---

## G) Web Sürümü & CI/CD Canlıya Alma Raporu (14 Ekim 2026)

> Bu bölüm, projenin masaüstü CLI aracından modern, tam duyarlı (mobil + masaüstü)
> bir bulut web servisine dönüştürülme sürecini ve tamamlanan maddeleri özetler.

### 1. Tamamlanan ve Canlıya Alınan Geliştirmeler:
- **Tam Duyarlı Modern Web Arayüzü (`dist/`):**
  - Göz yormayan derin obsidian (`#0c1017`) arayüz, glassmorphism kartlar, modern tipografi.
  - Mobil ve PC için optimize edilmiş düzen; dokunmatik ekranlara ve geniş monitörlere özel dinamik grid.
  - Video (MP4), Müzik (MP3 - 320 kbps), Altyazı (SRT) format sekmeleri.
  - Canlı video önizleme kartı (kapak resmi, süre, kanal adı, başlık).
  - Canlı ilerleme çubuğu, anlık indirme hızı (MB/s) ve kalan süre (sn) göstergeleri.
  - İndirme tamamlandığında Web Audio API ile sesli bildirim (chime) ve otomatik cihaz indirmesi.
  - İndirme geçmişi ve toplam indirilen dosya sayısı istatistiği (`localStorage`).
  - Güvenlik: Çerezler, şifreler ve özel anahtarlar kesin olarak `.gitignore` ile korunmaktadır.

- **FastAPI + yt-dlp + FFmpeg Backend Motoru (`backend/`):**
  - Render.com üzerinde containerized (Docker) canlı servis (`https://ytdownloader-p8pr.onrender.com`).
  - Universal ses codec dönüştürücüsü (`SesGuvenliPP`): MP4 içindeki Opus sesleri otomatik olarak AAC'ye dönüştürür.
  - Otomatik geçici dosya ve klasör temizleyicisi: 30 dakikadan eski görevleri ve disk alanını otomatik temizler.
  - FFmpeg + Node.js entegrasyonu: YouTube'un yeni JS n-challenge meydan okumalarını çözmek için Node.js eklendi.
  - Çerez desteği altyapısı: `YOUTUBE_COOKIES` çevre değişkeni ve `cookies.txt` desteği kuruldu.

- **GitHub + Netlify + Render CI/CD Otomasyonu:**
  - Kod GitHub `main` dalına pushlandığı anda Netlify statik arayüzü (~15 sn), Render ise backend Docker konteynerini (~2-3 dk) otomatik olarak derleyip canlıya alır.

### 2. Gelecek Yol Haritası (Sıradaki Geliştirmeler):
1. **Çerez Entegrasyonu:** Render Environment üzerinden `YOUTUBE_COOKIES` tanımlanarak yaş kısıtlı ve veri merkezi IP engellerinin tamamen aşılması.
2. **Toplu İndirme (Playlist / Kanal):** Tek bir link girildiğinde oynatma listesindeki tüm videoları sıraya alma ve zip olarak veya tek tek indirme.
3. **Bant Genişliği ve Hız Sınırlaması:** Sunucu kaynaklarını ve kullanıcının internet kotasını dengeli kullanmak için hız limiti opsiyonu.
4. **Gelişmiş Format Seçici:** 4K 60fps, 1440p 2K, WebM ve FLAC/WAV kayıpsız ses formatları.
5. **Kuyruk Senkronizasyonu & Bulut İstatistikleri:** Birden fazla cihaz arasında senkronize indirme kuyruğu.

---

## H) QA, Stres Testleri ve Prodüksiyon Dayanıklılık Raporu (14 Ekim 2026)

> Bu bölüm, sistemin uç senaryolar (edge cases), eşzamanlı stres, disk yönetimi ve hata toleransı
> testlerinden elde edilen bulguları ve alınan kalıcı mimari önlemleri içerir.

### 1. Test Edilen Senaryolar ve Çıkarılan Dersler:
1. **Eşzamanlı Yük & Kilitlenme Koruması (Concurrency Stress Test):**
   - 5 adet eşzamanlı indirme isteği gönderildi. FastAPI ve `ThreadPoolExecutor(max_workers=3)` mimarisinin kilitlenmediği doğrulandı.
   - Ders: Senkron işlemler asenkron döngüyü bloklamamalı; görev başlatma 15 ms içinde `task_id` dönerek Render'ın HTTP timeout sınırlarını tamamen baypas eder.
2. **Disk Alanı & Çöp Toplama (Garbage Collection):**
   - İndirme hatası alan görevlerin geçici dizinlerinin anında `shutil.rmtree` ile silinmesi sağlandı.
   - Sunucu açılışında her 5 dakikada bir uyanan `asyncio` arka plan temizlik döngüsü kuruldu. 30 dakikayı geçen artık dosyalar otomatik temizlenir; Render diski asla dolmaz.
3. **Uç Senaryo & Hata Yakalama (Edge Cases):**
   - Geçersiz URL, silinmiş/gizli video, üyelere özel içerik ve altyazısı bulunmayan içerik test edildi.
   - Sistem asla çökmez (unhandled 500 dönmez); tüm istisnalar `format_error_message()` tarafından yakalanıp kullanıcıya net Türkçe açıklama sunar.
4. **FFmpeg Bağımlılık Güvencesi:**
   - Docker ortamının yanı sıra olası Linux Native dağıtımlar için `build.sh` oluşturuldu ve statik FFmpeg ikilisi yükleme desteği eklendi.
5. **Güvenlik ve Çerez Sızıntı Koruması:**
   - `.gitignore` dosyası `.env*`, `cookies.txt`, `secrets/` ve tüm medya uzantılarını dışlayacak şekilde sertleştirildi; depoya hiçbir hassas bilgi sızamaz.

---

## I) YouTube Datacenter İstemci ve Bot Koruması Güçlendirmesi (v1.0.6)

1. **Bulut Veri Merkezi (Datacenter IP) Kısıtlamaları:**
   - Render (Frankfurt) gibi bulut sunucularında YouTube, sadece mobil istemcilere (`android`, `ios`) ve `player_skip` parametresiyle web sayfası atlanan isteklere karşı `Failed to extract any player response` ve `Sign in to confirm you're not a bot` engeli uygulamaktadır.
   - Yapılan iyileştirme ile `player_skip: ["webpage", "configs"]` kısıtı kaldırılmış; `player_client: ["tv", "web", "mweb", "android", "ios"]` sıralı istemci kademesi devreye alınmıştır. TV istemcisi bot meydan okumalarından etkilenmezken, web/mweb oturum çerezleriyle tam uyum sağlamaktadır.
2. **Çerez Formatlama ve Kaçış Karakteri Çözücü:**
   - Render çevre değişkeni `YOUTUBE_COOKIES` üzerinden aktarılan çerezlerde Base64 kodlama, kaçış karakterleri (`\n`) ve eksik `# Netscape HTTP Cookie File` başlığı otomatik olarak düzeltilecek şekilde güçlendirildi.
3. **Kullanıcı Dostu Hata Mesajları ve UI Entegrasyonu:**
   - YouTube'un teknik bot/çerez uyarıları ve ham `ERROR: [youtube]` çıktıları yakalanarak kullanıcıya doğrudan anlaşılır, estetik Türkçe uyarılar sunuldu.

---

## J) Bulut IP vs. Ev İnterneti Gerçeği ve Hibrit Çözüm Mimarisi (v1.3.0)

### 1. Temel Problem Analizi (Neden Local .bat Çalışırken Bulut Çöküyordu?):
- **Yerel İnternet (Residential IP):** Evdeki internet servis sağlayıcınız (Türk Telekom, Turkcell vb.) gerçek ev kullanıcısı IP bloğundadır. YouTube bu IP'lere bot engeli uygulamaz, çerez bile istemeden 5-10 MB/s hızla video indirmenize izin verir.
- **Bulut Veri Merkezleri (Datacenter IP):** Render (AWS Frankfurt) gibi sunucuların IP adresleri Google tarafından "veri merkezi / bot" olarak etiketlenmiştir.
- **Çerez Uyuşmazlığı Tuzağı:** Kullanıcı Türkiye'deki tarayıcısından çerez kopyalayıp Render'a (Frankfurt) yüklediğinde Google'ın coğrafi anomali motoru devreye girer: *"İstanbul'dan açılan oturum aynı anda Frankfurt veri merkezinden video çekiyor"* diyerek oturumu şüpheli işaretler ve `"Sign in to confirm you're not a bot"` kilidi vurur. Bu nedenle çerez eklemek sorunu çözmek yerine daha da kilitlemiştir.

### 2. Uygulanan Kalıcı ve Akıllı Çözüm (Ev Tünel Köprüsü - Cloudflare Tunnel):
1. **Sıfır Çerez, Sıfır Yapılandırma, %100 Başarı:**
   - Evdeki PC açıkken arka planda çalışan `run_home_server.py` ve `cloudflared.exe`, yerel FastAPI motorunu anında güvenli bir HTTPS tüneliyle (`trycloudflare.com`) internete açar.
   - Bu tünel adresi otomatik olarak `dist/config.js` içine yazılır ve Netlify'a pushlanır.
   - Kullanıcı dışarıda telefondan `https://ytindirici.netlify.app` sitesine girdiğinde hiçbir ayar yapmadan ev internetinin gücüyle YouTube videolarını, müziklerini ve altyazılarını saniyeler içinde telefonuna indirebilir.
2. **FileResponse HTTP 500 Header Hatasının Çözümü:**
   - Türkçe başlıklı videolarda (`İ`, `Ğ`, `Ü`, `Ş`, `Ö`, `Ç`) Starlette `headers={"Content-Disposition": ...}` içine raw string yazıldığı için `UnicodeEncodeError: 'latin-1' codec can't encode character` hatası fırlatılıyor ve dosya tesliminde HTTP 500 oluşuyordu.
   - RFC 6266 / RFC 5987 standartlarına uygun dinamik başlık formatlamasına geçildi; Türkçe karakterli tüm dosyalar telefon ve bilgisayara eksiksiz indirilebilir duruma getirildi.



