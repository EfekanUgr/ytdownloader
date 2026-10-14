/* ============================================================
   Downloader(+) — Uygulama Mantığı (Vanilla JS)
   Netlify ve Render için optimize edilmiş sağlam istemci.
   ============================================================ */

(() => {
  'use strict';

  // --- UYGULAMA DURUMU ---
  const State = {
    mode: 'video',
    quality: 'best',
    activeTaskId: null,
    pollTimer: null,
    isDownloading: false,
    history: JSON.parse(localStorage.getItem('dl_history') || '[]'),
    wakeAttempts: 0,
    maxWakeAttempts: 25, // 25 x 3s = 75 saniye (Render soğuk başlatma süresi)
  };

  // --- API URL TESPİTİ VE YÖNETİMİ ---
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
    const saved = localStorage.getItem('downloader_api_url');
    if (saved && saved.trim()) return cleanUrl(saved);
    if (window.CONFIG && window.CONFIG.DEFAULT_API_URL) {
      const def = cleanUrl(window.CONFIG.DEFAULT_API_URL);
      if (window.location.protocol === 'https:' && (def.includes('127.0.0.1') || def.includes('localhost'))) {
        return '';
      }
      return def;
    }
    return window.location.protocol === 'https:' ? '' : 'http://127.0.0.1:8000';
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

  const urlInput         = $('#urlInput');
  const pasteBtn         = $('#pasteBtn');
  const startDownloadBtn = $('#startDownloadBtn');
  const btnContent       = startDownloadBtn.querySelector('.btn-content');
  const btnSpinner       = startDownloadBtn.querySelector('.btn-spinner');

  const videoPreview     = $('#videoPreview');
  const previewThumb     = $('#previewThumb');
  const previewDuration  = $('#previewDuration');
  const previewTitle     = $('#previewTitle');
  const previewAuthor    = $('#previewAuthor');

  const quickApiBar      = $('#quickApiBar');
  const quickApiInput    = $('#quickApiInput');
  const quickApiSaveBtn  = $('#quickApiSaveBtn');
  const quickApiStatus   = $('#quickApiStatus');

  const qualityRow       = $('#qualityRow');
  const statusBox        = $('#statusBox');
  const statusBadge      = $('#statusBadge');
  const statusTitle      = $('#statusTitle');
  const statusPercent    = $('#statusPercent');
  const progressBar      = $('#progressBar');
  const statusSpeed      = $('#statusSpeed');
  const statusEta        = $('#statusEta');
  const errorMessage     = $('#errorMessage');
  const errorText        = $('#errorText');
  const saveBox          = $('#saveBox');
  const saveFileBtn      = $('#saveFileBtn');
  const savedFileSize    = $('#savedFileSize');

  const apiStatusBtn     = $('#apiStatusBtn');
  const apiStatusText    = $('#apiStatusText');
  const openSettingsBtn  = $('#openSettingsBtn');
  const closeSettingsBtn = $('#closeSettingsBtn');
  const settingsModal    = $('#settingsModal');
  const apiUrlInput      = $('#apiUrlInput');
  const testApiBtn       = $('#testApiBtn');
  const saveApiBtn       = $('#saveApiBtn');
  const testResult       = $('#testResult');

  const historySection   = $('#historySection');
  const historyList      = $('#historyList');
  const clearHistoryBtn  = $('#clearHistoryBtn');
  const toastBox         = $('#toastBox');

  // --- BAŞLATMA ---
  document.addEventListener('DOMContentLoaded', () => {
    const curApi = getApiUrl();
    apiUrlInput.value = curApi;
    if (quickApiInput) quickApiInput.value = (curApi && !curApi.includes('127.0.0.1')) ? curApi : '';
    
    checkApiHealth(true);
    renderHistory();
    setupEventListeners();
  });

  // --- OLAY DİNLEYİCİLERİ ---
  function setupEventListeners() {
    // Format Değişimi
    $$('.mode-card').forEach((card) => {
      card.addEventListener('click', () => {
        $$('.mode-card').forEach((c) => c.classList.remove('active'));
        card.classList.add('active');
        State.mode = card.dataset.mode;
        
        qualityRow.style.display = State.mode === 'video' ? 'flex' : 'none';
      });
    });

    // Kalite Seçimi
    $$('.quality-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        $$('.quality-chip').forEach((c) => c.classList.remove('active'));
        chip.classList.add('active');
        State.quality = chip.dataset.quality;
      });
    });

    // Panodan Yapıştır
    pasteBtn.addEventListener('click', async () => {
      try {
        const text = await navigator.clipboard.readText();
        if (text && text.trim()) {
          const val = text.trim();
          if (checkUrlForApi(val)) return;
          urlInput.value = val;
          onUrlChanged();
          toast('Link yapıştırıldı', 'info');
        }
      } catch (err) {
        urlInput.focus();
        toast('Panoya erişilemedi, lütfen elle yapıştırın', 'info');
      }
    });

    // URL Değişimi & Önizleme & Otomatik API Yakalama
    let previewDebounce = null;
    urlInput.addEventListener('input', () => {
      const val = urlInput.value.trim();
      if (checkUrlForApi(val)) return;

      clearTimeout(previewDebounce);
      previewDebounce = setTimeout(onUrlChanged, 500);
    });

    urlInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !State.isDownloading) {
        const val = urlInput.value.trim();
        if (checkUrlForApi(val)) return;
        startDownload();
      }
    });

    // Hızlı API Bağlan Butonu
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

    // İndir Butonu
    startDownloadBtn.addEventListener('click', () => {
      const val = urlInput.value.trim();
      if (checkUrlForApi(val)) return;
      startDownload();
    });

    // Ayarlar Modalı
    openSettingsBtn.addEventListener('click', () => openModal());
    apiStatusBtn.addEventListener('click', () => openModal());
    closeSettingsBtn.addEventListener('click', () => closeModal());
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
      toast('API adresi kaydedildi', 'success');
      closeModal();
      checkApiHealth(true);
    });

    // Geçmişi Temizle
    clearHistoryBtn.addEventListener('click', () => {
      State.history = [];
      localStorage.removeItem('dl_history');
      renderHistory();
      toast('Geçmiş temizlendi', 'info');
    });
  }

  // --- OTOMATİK API ADRESİ YAKALAMA ---
  function checkUrlForApi(val) {
    if (isApiUrl(val)) {
      setApiUrl(val);
      urlInput.value = '';
      videoPreview.style.display = 'none';
      toast('✔ Render API adresi algılandı ve otomatik bağlandı!', 'success');
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

    // Eğer canlı Netlify ortamındaysak ve geçerli bir API adresi henüz girilmemişse
    if (isHttps && isLocal) {
      clearInterval(healthSecondsTimer);
      healthInProgress = false;
      apiStatusBtn.className = 'api-pill warning';
      apiStatusText.textContent = 'API Ayarı Gerekli';

      if (quickApiBar) quickApiBar.style.display = 'block';
      if (quickApiStatus) {
        quickApiStatus.style.display = 'block';
        quickApiStatus.className = 'api-bar-status loading';
        quickApiStatus.textContent = 'ℹ Render web servisi linkinizi yukarıya girip Bağlan butonuna tıklayın.';
      }
      return;
    }

    if (healthInProgress) return;
    healthInProgress = true;
    clearInterval(healthSecondsTimer);

    apiStatusBtn.className = 'api-pill checking';
    apiStatusText.textContent = 'API Bağlanıyor...';

    if (quickApiBar) quickApiBar.style.display = 'block';
    if (quickApiStatus) {
      quickApiStatus.style.display = 'block';
      quickApiStatus.className = 'api-bar-status loading';
      quickApiStatus.textContent = '⏳ Render sunucusuna bağlanılıyor...';
    }

    let elapsed = 0;
    healthSecondsTimer = setInterval(() => {
      elapsed++;
      apiStatusText.textContent = `Sunucu Uyanıyor (${elapsed}s)...`;
      if (quickApiStatus) {
        quickApiStatus.textContent = `⏳ Render ücretsiz sunucusu uyandırılıyor (~30-50 sn sürebilir, geçen: ${elapsed} sn)... Lütfen bekleyin.`;
      }
    }, 1000);

    try {
      const controller = new AbortController();
      // Render ücretsiz soğuk başlatma 35-50 saniye sürebilir; erken kesmiyoruz (75 sn)
      const timeoutId = setTimeout(() => controller.abort(), 75000);

      const res = await fetch(`${base}/health`, {
        method: 'GET',
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      clearInterval(healthSecondsTimer);
      healthInProgress = false;

      if (res.ok) {
        apiStatusBtn.className = 'api-pill connected';
        apiStatusText.textContent = 'API Bağlı';

        if (quickApiStatus) {
          quickApiStatus.className = 'api-bar-status ok';
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

      apiStatusBtn.className = 'api-pill warning';
      apiStatusText.textContent = 'API Ayarı Gerekli';

      if (quickApiBar) quickApiBar.style.display = 'block';
      if (quickApiStatus) {
        quickApiStatus.style.display = 'block';
        quickApiStatus.className = 'api-bar-status fail';
        const isAbort = err.name === 'AbortError';
        quickApiStatus.textContent = isAbort
          ? '✖ Sunucu 75 saniye içinde yanıt vermedi. Render dashboard\'undan servisin durumunu kontrol edin.'
          : '✖ Sunucuya ulaşılamadı. Lütfen Render linkinizi ve servisin aktif olduğunu kontrol edin.';
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
    testResult.className = 'test-result';
    testResult.textContent = 'Test ediliyor (uykudaysa ~30 sn sürebilir)...';

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 65000);
      const res = await fetch(`${candidate}/health`, { method: 'GET', signal: controller.signal });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        showTestResult(true, `✔ Bağlantı Başarılı! (Versiyon: ${data.version || '1.0.0'}, FFmpeg: ${data.ffmpeg || 'Hazır'})`);
      } else {
        showTestResult(false, `✖ Sunucu hata döndürdü (HTTP ${res.status})`);
      }
    } catch (e) {
      showTestResult(false, '✖ Sunucuya erişilemedi. Adresin doğru olduğundan ve Render servisinizin aktif olduğundan emin olun.');
    }
  }

  function showTestResult(isOk, msg) {
    testResult.style.display = 'block';
    testResult.className = 'test-result ' + (isOk ? 'ok' : 'fail');
    testResult.textContent = msg;
  }

  // --- ÖNİZLEME BİLGİSİ ---
  async function onUrlChanged() {
    const url = urlInput.value.trim();
    if (!url.startsWith('http')) {
      videoPreview.style.display = 'none';
      return;
    }

    try {
      const base = getApiUrl();
      const res = await fetch(`${base}/api/info`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      if (!res.ok) return;

      const data = await res.json();
      if (data && data.title) {
        previewTitle.textContent = data.title;
        previewAuthor.textContent = data.uploader || 'YouTube';
        previewDuration.textContent = data.duration || '';
        if (data.thumbnail) {
          previewThumb.src = data.thumbnail;
          previewThumb.style.display = 'block';
        } else {
          previewThumb.style.display = 'none';
        }
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

    const base = getApiUrl();
    try {
      const res = await fetch(`${base}/api/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          mode: State.mode,
          quality: State.quality
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `Sunucu hatası: HTTP ${res.status}`);
      }

      const data = await res.json();
      State.activeTaskId = data.task_id;
      startPolling(data.task_id);

    } catch (err) {
      showError(err.message || 'API sunucusuna bağlanılamadı. Sağ üstteki API ayarını kontrol edin.');
      setLoading(false);
    }
  }

  function startPolling(taskId) {
    if (State.pollTimer) clearInterval(State.pollTimer);
    State.pollTimer = setInterval(() => pollStatus(taskId), 750);
    pollStatus(taskId);
  }

  async function pollStatus(taskId) {
    const base = getApiUrl();
    try {
      const res = await fetch(`${base}/api/status/${taskId}`);
      if (!res.ok) return;
      const data = await res.json();

      updateProgressUI(data);

      if (data.status === 'completed') {
        finishDownload(data);
      } else if (data.status === 'error') {
        clearInterval(State.pollTimer);
        showError(data.error || 'İndirme sırasında bir hata meydana geldi.');
        setLoading(false);
      }
    } catch (err) {
      // Ağ dalgalanması
    }
  }

  function updateProgressUI(data) {
    statusBox.style.display = 'block';
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
    statusBadge.className = `status-badge ${cur.class}`;

    statusSpeed.textContent = data.speed || '';
    statusEta.textContent = data.eta ? `Kalan süre: ~${data.eta} sn` : '';
  }

  function finishDownload(data) {
    clearInterval(State.pollTimer);
    setLoading(false);

    progressBar.style.width = '100%';
    statusPercent.textContent = '100%';
    statusSpeed.textContent = data.file_size ? `Boyut: ${data.file_size}` : '';
    statusEta.textContent = '';

    const base = getApiUrl();
    const downloadUrl = `${base}/api/file/${data.id}`;

    // Otomatik doğrudan indirme
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = data.file_name || 'indirilen_dosya';
    document.body.appendChild(a);
    a.click();
    a.remove();

    // Manuel buton
    saveFileBtn.href = downloadUrl;
    savedFileSize.textContent = data.file_size || '';
    saveBox.style.display = 'block';

    toast('İndirme tamamlandı! Dosya cihazınıza kaydediliyor.', 'success');
    addToHistory(data);
  }

  function resetStatusBox() {
    statusBox.style.display = 'block';
    errorMessage.style.display = 'none';
    saveBox.style.display = 'none';
    progressBar.style.width = '0%';
    statusPercent.textContent = '0%';
    statusSpeed.textContent = '';
    statusEta.textContent = '';
    statusTitle.textContent = 'Kuyruğa alınıyor...';
    statusBadge.textContent = 'Sırada';
    statusBadge.className = 'status-badge queued';
  }

  function showError(msg) {
    errorMessage.style.display = 'flex';
    errorText.textContent = msg;
    statusBadge.textContent = 'Hata';
    statusBadge.className = 'status-badge error';
    toast(msg, 'error');
  }

  function setLoading(loading) {
    State.isDownloading = loading;
    startDownloadBtn.disabled = loading;
    btnContent.style.display = loading ? 'none' : 'flex';
    btnSpinner.style.display = loading ? 'inline-block' : 'none';
  }

  // --- GEÇMİŞ YÖNETİMİ ---
  function addToHistory(item) {
    const entry = {
      id: item.id,
      title: item.title || 'İsimsiz İçerik',
      mode: State.mode,
      file_size: item.file_size || '',
      time: new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }),
    };

    State.history.unshift(entry);
    if (State.history.length > 8) State.history.pop();
    localStorage.setItem('dl_history', JSON.stringify(State.history));
    renderHistory();
  }

  function renderHistory() {
    if (!State.history.length) {
      historySection.style.display = 'none';
      return;
    }

    historySection.style.display = 'block';
    const base = getApiUrl();
    const icons = { video: '🎬', music: '🎵', subtitle: '📝' };

    historyList.innerHTML = State.history.map((h) => `
      <div class="history-item">
        <div class="history-left">
          <div class="history-icon ${h.mode}">${icons[h.mode] || '📄'}</div>
          <div>
            <div class="history-title">${escapeHtml(h.title)}</div>
            <div class="history-meta">${h.time} ${h.file_size ? `· ${h.file_size}` : ''}</div>
          </div>
        </div>
        <a class="history-dl" href="${base}/api/file/${h.id}" download title="Tekrar İndir">İndir</a>
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

  // --- TOAST BİLDİRİM ---
  function toast(message, type = 'info') {
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = message;
    toastBox.appendChild(el);

    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(10px)';
      el.style.transition = 'all 0.3s ease';
      setTimeout(() => el.remove(), 300);
    }, 4000);
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
  }
})();
