/* ============================================================
   Downloader(+) — Modern Uygulama Mantığı (Vanilla JS)
   Netlify & Render ile optimize edilmiş, mobil ve masaüstü uyumlu.
   ============================================================ */

(() => {
  'use strict';

  // --- UYGULAMA DURUMU (STATE) ---
  const State = {
    mode: 'video',          // 'video' | 'music' | 'subtitle'
    quality: 'best',        // 'best' | '1080' | '720' | '480'
    activeTaskId: null,
    pollTimer: null,
    isDownloading: false,
    history: JSON.parse(localStorage.getItem('dl_history') || '[]'),
    stats: JSON.parse(localStorage.getItem('dl_stats') || '{"count": 0, "sizeBytes": 0}'),
  };

  // --- URL TESPİTİ VE YÖNETİMİ ---
  function isApiUrl(url) {
    if (!url) return false;
    const u = url.toLowerCase().trim();
    return (
      u.includes('onrender.com') ||
      u.includes('railway.app') ||
      u.includes('koyeb.app') ||
      u.includes(':8000') ||
      u.includes(':5000')
    );
  }

  function cleanUrl(raw) {
    let clean = (raw || '').trim().replace(/\/+$/, '');
    if (clean.startsWith('http://') && !clean.includes('localhost') && !clean.includes('127.0.0.1')) {
      clean = clean.replace('http://', 'https://');
    }
    return clean;
  }

  function getApiUrl() {
    const isHttps = window.location.protocol === 'https:';

    // 1. window.CONFIG içindeki aktif köprü/tünel adresi (en yüksek öncelik)
    if (window.CONFIG && window.CONFIG.DEFAULT_API_URL) {
      const def = cleanUrl(window.CONFIG.DEFAULT_API_URL);
      // Eski onrender.com veya uyumsuz eski kayıtları temizle
      const saved = localStorage.getItem('downloader_api_url');
      if (saved && (saved.includes('onrender.com') || saved !== def)) {
        localStorage.removeItem('downloader_api_url');
      }
      if (def && (!isHttps || def.startsWith('https://'))) {
        return def;
      }
    }

    // 2. Kullanıcının elle girdiği özel adres
    const validSaved = localStorage.getItem('downloader_api_url');
    if (validSaved && validSaved.trim() && (!isHttps || validSaved.startsWith('https://'))) {
      return cleanUrl(validSaved);
    }

    // 3. Yedek: Render adresi
    if (window.CONFIG && window.CONFIG.RENDER_API_URL) {
      return cleanUrl(window.CONFIG.RENDER_API_URL);
    }

    return isHttps ? '' : 'http://127.0.0.1:8000';
  }

  async function apiFetch(endpoint, options = {}) {
    const primary = getApiUrl();
    const fallback = (window.CONFIG?.DEFAULT_API_URL && primary !== window.CONFIG.DEFAULT_API_URL)
      ? window.CONFIG.DEFAULT_API_URL
      : window.CONFIG?.RENDER_API_URL;

    try {
      const res = await fetch(`${primary}${endpoint}`, options);
      if (res.ok) return { res, ok: true, url: primary };

      const clone = res.clone();
      const errJson = await clone.json().catch(() => null);
      const isBlock = res.status >= 500 || (errJson && JSON.stringify(errJson).includes('kısıtladı'));

      if (isBlock && fallback && fallback !== primary) {
        console.warn(`[Downloader] ${primary} yanıt veremedi, yedek (${fallback}) deneniyor...`);
        const fbRes = await fetch(`${fallback}${endpoint}`, options);
        if (fbRes.ok) {
          setApiUrl(fallback);
          return { res: fbRes, ok: true, url: fallback };
        }
      }
      return { res, ok: false, url: primary };
    } catch (err) {
      if (fallback && fallback !== primary) {
        console.warn(`[Downloader] ${primary} erişilemedi, yedek (${fallback}) deneniyor...`);
        try {
          const fbRes = await fetch(`${fallback}${endpoint}`, options);
          if (fbRes.ok) {
            setApiUrl(fallback);
            return { res: fbRes, ok: true, url: fallback };
          }
          return { res: fbRes, ok: false, url: fallback };
        } catch {
          throw err;
        }
      }
      throw err;
    }
  }

  function setApiUrl(url) {
    const clean = cleanUrl(url);
    localStorage.setItem('downloader_api_url', clean);
    if (apiUrlInput) apiUrlInput.value = clean;
    if (quickApiInput) quickApiInput.value = clean;
  }

  // --- DOM ELEMENTLERİ ---
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // Link ve İşlem
  const urlInput           = $('#urlInput');
  const clearInputBtn      = $('#clearInputBtn');
  const pasteBtn           = $('#pasteBtn');
  const startDownloadBtn   = $('#startDownloadBtn');
  const btnText            = $('#btnText');
  const btnSpinner         = startDownloadBtn.querySelector('.btn-spinner');

  // Önizleme
  const videoPreview       = $('#videoPreview');
  const previewThumb       = $('#previewThumb');
  const previewDuration    = $('#previewDuration');
  const previewTitle       = $('#previewTitle');
  const previewAuthor      = $('#previewAuthor');
  const previewFormatLabel = $('#previewFormatLabel');

  // Mod & Kalite
  const qualityRow         = $('#qualityRow');
  const musicNotice        = $('#musicNotice');
  const subtitleNotice     = $('#subtitleNotice');

  // Hızlı API Çubuğu
  const quickApiBar        = $('#quickApiBar');
  const quickApiInput      = $('#quickApiInput');
  const quickApiSaveBtn    = $('#quickApiSaveBtn');
  const quickApiStatus     = $('#quickApiStatus');

  // İlerleme & Durum
  const statusBox          = $('#statusBox');
  const statusBadge        = $('#statusBadge');
  const statusTitle        = $('#statusTitle');
  const statusPercent      = $('#statusPercent');
  const progressBar        = $('#progressBar');
  const statusSpeed        = $('#statusSpeed');
  const statusEta          = $('#statusEta');
  const errorMessage       = $('#errorMessage');
  const errorText          = $('#errorText');
  const saveBox            = $('#saveBox');
  const saveFileBtn        = $('#saveFileBtn');
  const savedFileSize      = $('#savedFileSize');

  // Header & Durum
  const apiStatusBtn       = $('#apiStatusBtn');
  const apiStatusText      = $('#apiStatusText');
  const openSettingsBtn    = $('#openSettingsBtn');
  const closeSettingsBtn   = $('#closeSettingsBtn');
  const settingsModal      = $('#settingsModal');
  const apiUrlInput        = $('#apiUrlInput');
  const testApiBtn         = $('#testApiBtn');
  const saveApiBtn         = $('#saveApiBtn');
  const testResult         = $('#testResult');

  // Geçmiş & İstatistik
  const historySection     = $('#historySection');
  const historyList        = $('#historyList');
  const historyStats       = $('#historyStats');
  const clearHistoryBtn    = $('#clearHistoryBtn');
  const toastBox           = $('#toastBox');

  // --- BAŞLATMA (INIT) ---
  document.addEventListener('DOMContentLoaded', () => {
    const curApi = getApiUrl();
    if (apiUrlInput) apiUrlInput.value = curApi;
    if (quickApiInput) quickApiInput.value = (curApi && !curApi.includes('127.0.0.1')) ? curApi : '';
    
    checkApiHealth(true);
    renderHistory();
    updateButtonLabel();
    setupEventListeners();
  });

  // --- OLAY DİNLEYİCİLERİ ---
  function setupEventListeners() {

    // Mod Sekmeleri (Video / Müzik / Altyazı)
    $$('.tab-item').forEach((tab) => {
      tab.addEventListener('click', () => {
        $$('.tab-item').forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        State.mode = tab.dataset.mode;

        // Arayüzü seçilen moda göre güncelle
        if (qualityRow) qualityRow.style.display = State.mode === 'video' ? 'flex' : 'none';
        if (musicNotice) musicNotice.style.display = State.mode === 'music' ? 'flex' : 'none';
        if (subtitleNotice) subtitleNotice.style.display = State.mode === 'subtitle' ? 'flex' : 'none';

        updateButtonLabel();
        updatePreviewBadge();
      });
    });

    // Kalite Seçimi
    $$('.chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        $$('.chip').forEach((c) => c.classList.remove('active'));
        chip.classList.add('active');
        State.quality = chip.dataset.quality;
        updatePreviewBadge();
      });
    });

    // Panodan Yapıştır Butonu
    pasteBtn.addEventListener('click', async () => {
      try {
        const text = await navigator.clipboard.readText();
        if (text && text.trim()) {
          const val = text.trim();
          if (checkUrlForApi(val)) return;
          urlInput.value = val;
          toggleClearBtn();
          onUrlChanged();
          toast('Link panodan yapıştırıldı', 'info');
        }
      } catch (err) {
        urlInput.focus();
        toast('Panoya doğrudan erişilemedi, lütfen elle yapıştırın (Ctrl + V)', 'info');
      }
    });

    // Temizle Butonu
    if (clearInputBtn) {
      clearInputBtn.addEventListener('click', () => {
        urlInput.value = '';
        toggleClearBtn();
        videoPreview.style.display = 'none';
        urlInput.focus();
      });
    }

    // URL Girişi ve Önizleme Tetikleme
    let previewDebounce = null;
    urlInput.addEventListener('input', () => {
      const val = urlInput.value.trim();
      toggleClearBtn();
      if (checkUrlForApi(val)) return;

      clearTimeout(previewDebounce);
      previewDebounce = setTimeout(onUrlChanged, 450);
    });

    urlInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !State.isDownloading) {
        const val = urlInput.value.trim();
        if (checkUrlForApi(val)) return;
        startDownload();
      }
    });

    // Hızlı API Bağlantı Çubuğu
    if (quickApiSaveBtn) {
      quickApiSaveBtn.addEventListener('click', () => {
        const val = quickApiInput.value.trim();
        if (!val) {
          toast('Lütfen Render linkinizi girin', 'error');
          return;
        }
        setApiUrl(val);
        toast('API adresi kaydedildi, bağlanılıyor...', 'info');
        checkApiHealth(true);
      });
    }

    if (quickApiInput) {
      quickApiInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          if (quickApiSaveBtn) quickApiSaveBtn.click();
        }
      });
    }

    // Ana İndirme Butonu
    startDownloadBtn.addEventListener('click', () => {
      const val = urlInput.value.trim();
      if (checkUrlForApi(val)) return;
      startDownload();
    });

    // Ayarlar Modalı
    openSettingsBtn.addEventListener('click', openModal);
    apiStatusBtn.addEventListener('click', openModal);
    closeSettingsBtn.addEventListener('click', closeModal);
    settingsModal.addEventListener('click', (e) => {
      if (e.target === settingsModal) closeModal();
    });

    testApiBtn.addEventListener('click', testEnteredApi);
    saveApiBtn.addEventListener('click', () => {
      const val = apiUrlInput.value.trim();
      if (!val) {
        toast('API adresi boş bırakılamaz', 'error');
        return;
      }
      setApiUrl(val);
      toast('API adresi güncellendi', 'success');
      closeModal();
      checkApiHealth(true);
    });

    // Geçmişi Temizle
    clearHistoryBtn.addEventListener('click', () => {
      State.history = [];
      State.stats = { count: 0, sizeBytes: 0 };
      localStorage.removeItem('dl_history');
      localStorage.removeItem('dl_stats');
      renderHistory();
      toast('İndirme geçmişi temizlendi', 'info');
    });
  }

  function toggleClearBtn() {
    if (clearInputBtn) {
      clearInputBtn.style.display = urlInput.value.trim() ? 'block' : 'none';
    }
  }

  function updateButtonLabel() {
    if (!btnText) return;
    if (State.mode === 'video') {
      btnText.textContent = 'Videoyu İndir (MP4)';
    } else if (State.mode === 'music') {
      btnText.textContent = 'Müziği İndir (MP3 · 320k)';
    } else if (State.mode === 'subtitle') {
      btnText.textContent = 'Altyazıyı İndir (SRT)';
    }
  }

  function updatePreviewBadge() {
    if (!previewFormatLabel) return;
    if (State.mode === 'video') {
      const qMap = { best: 'En İyi', '1080': '1080p', '720': '720p', '480': '480p' };
      previewFormatLabel.textContent = `MP4 Video (${qMap[State.quality] || 'FHD'})`;
    } else if (State.mode === 'music') {
      previewFormatLabel.textContent = 'MP3 Müzik (320 kbps)';
    } else if (State.mode === 'subtitle') {
      previewFormatLabel.textContent = 'SRT Altyazı';
    }
  }

  // --- OTOMATİK API ADRESİ YAKALAMA ---
  function checkUrlForApi(val) {
    if (isApiUrl(val)) {
      setApiUrl(val);
      urlInput.value = '';
      toggleClearBtn();
      videoPreview.style.display = 'none';
      toast('✔ Render API adresi algılandı ve kaydedildi!', 'success');
      checkApiHealth(true);
      return true;
    }
    return false;
  }

  // --- API SAĞLIK KONTROLÜ & RENDER UYANDIRMA ---
  let healthSecondsTimer = null;
  let healthInProgress = false;

  async function checkApiHealth(autoRetry = true) {
    const base = getApiUrl();
    const isHttps = window.location.protocol === 'https:';
    const isLocal = !base || base.includes('127.0.0.1') || base.includes('localhost');

    // Eğer canlı Netlify ortamındaysak ve geçerli bir uzak API linki girilmemişse
    if (isHttps && isLocal) {
      clearInterval(healthSecondsTimer);
      healthInProgress = false;
      apiStatusBtn.className = 'status-pill warning';
      apiStatusText.textContent = 'API Ayarı Gerekli';

      if (quickApiBar) quickApiBar.style.display = 'flex';
      if (quickApiStatus) {
        quickApiStatus.style.display = 'block';
        quickApiStatus.className = 'notice-status fail';
        quickApiStatus.textContent = 'ℹ Render web servisi linkinizi yukarıdaki kutuya yapıştırıp Bağlan butonuna tıklayın.';
      }
      return;
    }

    if (healthInProgress) return;
    healthInProgress = true;
    clearInterval(healthSecondsTimer);

    apiStatusBtn.className = 'status-pill checking';
    apiStatusText.textContent = 'API Bağlanıyor...';

    if (quickApiStatus) {
      quickApiStatus.style.display = 'block';
      quickApiStatus.className = 'notice-status loading';
      quickApiStatus.textContent = '⏳ Render sunucusuna bağlanılıyor...';
    }

    let elapsed = 0;
    healthSecondsTimer = setInterval(() => {
      elapsed++;
      apiStatusText.textContent = `Sunucu Uyanıyor (${elapsed}s)...`;
      if (quickApiStatus) {
        quickApiStatus.textContent = `⏳ Render ücretsiz sunucusu uyandırılıyor (~30-50 sn sürebilir, geçen: ${elapsed} sn)...`;
      }
    }, 1000);

    try {
      const controller = new AbortController();
      // Render soğuk başlatma 35-50 saniye sürebilir; 75 saniyeye kadar bekle
      const timeoutId = setTimeout(() => controller.abort(), 75000);

      const res = await fetch(`${base}/health`, {
        method: 'GET',
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      clearInterval(healthSecondsTimer);
      healthInProgress = false;

      if (res.ok) {
        apiStatusBtn.className = 'status-pill connected';
        apiStatusText.textContent = 'API Bağlı';

        if (quickApiStatus) {
          quickApiStatus.className = 'notice-status ok';
          quickApiStatus.textContent = '✔ Bağlantı Başarılı! Sunucu hazır ve aktif.';
          setTimeout(() => {
            if (quickApiBar) quickApiBar.style.display = 'none';
          }, 2000);
        }
        return;
      }
      throw new Error(`HTTP ${res.status}`);
    } catch (err) {
      clearInterval(healthSecondsTimer);
      healthInProgress = false;

      apiStatusBtn.className = 'status-pill warning';
      apiStatusText.textContent = 'API Ayarı Gerekli';

      if (quickApiBar) quickApiBar.style.display = 'flex';
      if (quickApiStatus) {
        quickApiStatus.style.display = 'block';
        quickApiStatus.className = 'notice-status fail';
        const isAbort = err.name === 'AbortError';
        quickApiStatus.textContent = isAbort
          ? '✖ Sunucu 75 saniye içinde yanıt vermedi. Render dashboard\'undan servisin durumunu kontrol edin.'
          : '✖ Sunucuya ulaşılamadı. Lütfen Render linkinizin doğruluğunu ve servisin çalıştığını kontrol edin.';
      }
    }
  }

  async function testEnteredApi() {
    const candidate = cleanUrl(apiUrlInput.value);
    if (!candidate) {
      showTestResult(false, 'Lütfen geçerli bir URL girin.');
      return;
    }

    testResult.style.display = 'block';
    testResult.className = 'test-feedback';
    testResult.textContent = 'Test ediliyor (uykudaysa ~30 sn sürebilir)...';

    const t0 = performance.now();
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 65000);
      const res = await fetch(`${candidate}/health`, { method: 'GET', signal: controller.signal });
      clearTimeout(timeoutId);
      const ping = Math.round(performance.now() - t0);

      if (res.ok) {
        const data = await res.json();
        showTestResult(true, `✔ Bağlantı Başarılı! (${ping} ms)\nVersiyon: ${data.version || '1.0.0'} · FFmpeg: ${data.ffmpeg || 'Hazır'}`);
      } else {
        showTestResult(false, `✖ Sunucu hata döndürdü (HTTP ${res.status})`);
      }
    } catch (e) {
      showTestResult(false, '✖ Sunucuya erişilemedi. Adresin doğru olduğundan ve Render servisinizin aktif olduğundan emin olun.');
    }
  }

  function showTestResult(isOk, msg) {
    testResult.style.display = 'block';
    testResult.className = 'test-feedback ' + (isOk ? 'ok' : 'fail');
    testResult.textContent = msg;
  }

  // --- VİDEO ÖNİZLEME BİLGİSİ ---
  async function onUrlChanged() {
    const url = urlInput.value.trim();
    if (!url.startsWith('http')) {
      videoPreview.style.display = 'none';
      return;
    }

    try {
      const { res, ok } = await apiFetch('/api/info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      if (!ok) return;

      const data = await res.json();
      if (data && data.title) {
        previewTitle.textContent = data.title;
        previewAuthor.textContent = data.uploader || 'Web Medyası';
        previewDuration.textContent = data.duration || '';
        if (data.thumbnail) {
          previewThumb.src = data.thumbnail;
          previewThumb.style.display = 'block';
        } else {
          previewThumb.style.display = 'none';
        }
        updatePreviewBadge();
        videoPreview.style.display = 'flex';
      }
    } catch {
      // Sessizce geç
    }
  }

  // --- İNDİRME AKIŞI ---
  async function startDownload() {
    const url = urlInput.value.trim();
    if (!url) {
      urlInput.focus();
      toast('Lütfen bir video linki yapıştırın', 'error');
      return;
    }
    if (!url.startsWith('http')) {
      toast('Geçersiz link! (http veya https ile başlamalı)', 'error');
      return;
    }

    setLoading(true);
    resetStatusBox();

    try {
      const { res, ok, url: activeBase } = await apiFetch('/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          mode: State.mode,
          quality: State.quality
        })
      });

      if (!ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `Sunucu hatası: HTTP ${res.status}`);
      }

      const data = await res.json();
      State.activeTaskId = data.task_id;
      startPolling(data.task_id, activeBase);

    } catch (err) {
      showError(err.message || 'API sunucusuna bağlanılamadı. Sağ üstteki API ayarını kontrol edin.');
      setLoading(false);
    }
  }

  function startPolling(taskId, activeBase) {
    if (State.pollTimer) clearInterval(State.pollTimer);
    State.pollTimer = setInterval(() => pollStatus(taskId, activeBase), 750);
    pollStatus(taskId, activeBase);
  }

  async function pollStatus(taskId, activeBase) {
    const base = activeBase || getApiUrl();
    try {
      const res = await fetch(`${base}/api/status/${taskId}`);
      if (!res.ok) return;
      const data = await res.json();

      updateProgressUI(data);

      if (data.status === 'completed') {
        finishDownload(data, activeBase);
      } else if (data.status === 'error') {
        clearInterval(State.pollTimer);
        showError(data.error || 'İndirme sırasında bir hata meydana geldi.');
        setLoading(false);
      }
    } catch (err) {
      // Ağ dalgalanmasında sessizce devam et
    }
  }

  function updateProgressUI(data) {
    statusBox.style.display = 'flex';
    statusTitle.textContent = data.title || 'İşleniyor...';

    const pct = Math.max(0, Math.min(100, Math.round(data.progress || 0)));
    progressBar.style.width = `${pct}%`;
    statusPercent.textContent = `${pct}%`;

    const statusMap = {
      queued:      { text: 'Sırada', class: 'queued' },
      starting:    { text: 'Hazırlanıyor', class: 'starting' },
      downloading: { text: 'İndiriliyor', class: 'downloading' },
      processing:  { text: 'Dönüştürülüyor', class: 'processing' },
      completed:   { text: 'Tamamlandı', class: 'completed' },
      error:       { text: 'Hata', class: 'error' },
    };

    const cur = statusMap[data.status] || { text: data.status, class: 'queued' };
    statusBadge.textContent = cur.text;
    statusBadge.className = `live-badge ${cur.class}`;

    statusSpeed.textContent = data.speed ? `🚀 ${data.speed}` : '';
    statusEta.textContent = data.eta ? `⏱ Kalan: ~${data.eta} sn` : '';
  }

  function finishDownload(data, activeBase) {
    clearInterval(State.pollTimer);
    setLoading(false);

    progressBar.style.width = '100%';
    statusPercent.textContent = '100%';
    statusSpeed.textContent = data.file_size ? `Boyut: ${data.file_size}` : '';
    statusEta.textContent = '';

    const base = activeBase || getApiUrl();
    const downloadUrl = `${base}/api/file/${data.id}`;

    // Otomatik indirmeyi tetikle
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = data.file_name || 'indirilen_dosya';
    document.body.appendChild(a);
    a.click();
    a.remove();

    // Manuel butonu da hazırla
    saveFileBtn.href = downloadUrl;
    savedFileSize.textContent = data.file_size || 'Hazır';
    saveBox.style.display = 'flex';

    // Ses efekti ve bildirim
    playCompletionSound();
    toast('🎉 İndirme tamamlandı! Dosya cihazınıza kaydediliyor.', 'success');
    addToHistory(data);
  }

  function resetStatusBox() {
    statusBox.style.display = 'flex';
    errorMessage.style.display = 'none';
    saveBox.style.display = 'none';
    progressBar.style.width = '0%';
    statusPercent.textContent = '0%';
    statusSpeed.textContent = '';
    statusEta.textContent = '';
    statusTitle.textContent = 'Kuyruğa alınıyor...';
    statusBadge.textContent = 'Sırada';
    statusBadge.className = 'live-badge queued';
  }

  function showError(msg) {
    errorMessage.style.display = 'flex';
    errorText.textContent = msg;
    statusBadge.textContent = 'Hata';
    statusBadge.className = 'live-badge error';
    toast(msg, 'error');
  }

  function setLoading(loading) {
    State.isDownloading = loading;
    startDownloadBtn.disabled = loading;
    const btnContentEl = startDownloadBtn.querySelector('.btn-content');
    if (btnContentEl) btnContentEl.style.display = loading ? 'none' : 'flex';
    if (btnSpinner) btnSpinner.style.display = loading ? 'inline-flex' : 'none';
  }

  // --- SES BİLDİRİMİ (WEB AUDIO API) ---
  function playCompletionSound() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.12); // A5

      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + 0.35);
    } catch {
      // Sessizce geç
    }
  }

  // --- GEÇMİŞ VE İSTATİSTİK YÖNETİMİ ---
  function addToHistory(item) {
    const entry = {
      id: item.id,
      title: item.title || 'İsimsiz İçerik',
      mode: State.mode,
      file_size: item.file_size || '',
      time: new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }),
    };

    State.history.unshift(entry);
    if (State.history.length > 10) State.history.pop();
    localStorage.setItem('dl_history', JSON.stringify(State.history));

    State.stats.count = (State.stats.count || 0) + 1;
    localStorage.setItem('dl_stats', JSON.stringify(State.stats));

    renderHistory();
  }

  function renderHistory() {
    if (!State.history.length) {
      historySection.style.display = 'none';
      return;
    }

    historySection.style.display = 'flex';
    if (historyStats) {
      historyStats.textContent = `${State.stats.count || State.history.length} dosya indirildi`;
    }

    const base = getApiUrl();
    const icons = { video: '🎬', music: '🎵', subtitle: '📝' };

    historyList.innerHTML = State.history.map((h) => `
      <div class="history-row">
        <div class="row-left">
          <div class="row-icon ${h.mode}">${icons[h.mode] || '📄'}</div>
          <div class="row-info">
            <span class="row-title">${escapeHtml(h.title)}</span>
            <span class="row-meta">${h.time} ${h.file_size ? `· ${h.file_size}` : ''}</span>
          </div>
        </div>
        <a class="row-dl-btn" href="${base}/api/file/${h.id}" download title="Tekrar İndir">İndir</a>
      </div>
    `).join('');
  }

  // --- MODAL FONKSİYONLARI ---
  function openModal() {
    apiUrlInput.value = getApiUrl();
    testResult.style.display = 'none';
    settingsModal.style.display = 'flex';
  }

  function closeModal() {
    settingsModal.style.display = 'none';
  }

  // --- TOAST BİLDİRİMLERİ ---
  function toast(message, type = 'info') {
    const el = document.createElement('div');
    el.className = `toast-item ${type}`;
    el.textContent = message;
    toastBox.appendChild(el);

    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(8px)';
      el.style.transition = 'all 0.25s ease';
      setTimeout(() => el.remove(), 260);
    }, 4000);
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
  }
})();
