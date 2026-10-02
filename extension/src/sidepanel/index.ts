import { TabAnalysisState, AnalyzeResponse } from '../shared/types';

// DOM Elements
const stateIdle = document.getElementById('state-idle') as HTMLDivElement;
const stateLoading = document.getElementById('state-loading') as HTMLDivElement;
const stateSuccess = document.getElementById('state-success') as HTMLDivElement;
const stateError = document.getElementById('state-error') as HTMLDivElement;

const loadingTextPreview = document.getElementById('loading-text-preview') as HTMLElement;
const loadingStepText = document.getElementById('loading-step-text') as HTMLParagraphElement;

const successTextPreview = document.getElementById('success-text-preview') as HTMLParagraphElement;
const btnReadMore = document.getElementById('btn-read-more') as HTMLButtonElement;

const serviceWarning = document.getElementById('service-warning') as HTMLDivElement;

const resultVerdict = document.getElementById('result-verdict') as HTMLDivElement;
const verdictIcon = document.getElementById('verdict-icon') as HTMLSpanElement;
const verdictText = document.getElementById('verdict-text') as HTMLSpanElement;

const resultConfidenceText = document.getElementById('result-confidence-text') as HTMLSpanElement;
const resultConfidenceBar = document.getElementById('result-confidence-bar') as HTMLDivElement;
const confidenceProgress = document.getElementById('confidence-progress') as HTMLDivElement;

const resultExplanation = document.getElementById('result-explanation') as HTMLParagraphElement;
const resultSources = document.getElementById('result-sources') as HTMLUListElement;

const errorMessage = document.getElementById('error-message') as HTMLParagraphElement;
const btnRetry = document.getElementById('btn-retry') as HTMLButtonElement;
const btnCopy = document.getElementById('btn-copy') as HTMLButtonElement;

let currentTabId: number | null = null;
let loadingInterval: number | null = null;

async function init() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tabs.length > 0 && tabs[0].id) {
    currentTabId = tabs[0].id;
    await loadState(currentTabId);
    
    // Clear badge when side panel is opened
    chrome.action.setBadgeText({ text: '', tabId: currentTabId }).catch(() => {});
  }

  // Listen for state changes
  chrome.storage.session.onChanged.addListener((changes) => {
    if (currentTabId && changes[`tabState_${currentTabId}`]) {
      renderState(changes[`tabState_${currentTabId}`].newValue as TabAnalysisState);
    }
  });

  // Handle active tab change
  chrome.tabs.onActivated.addListener(async (activeInfo) => {
    currentTabId = activeInfo.tabId;
    await loadState(currentTabId);
  });

  // Handle tab update
  chrome.tabs.onUpdated.addListener(async (tabId, changeInfo) => {
    if (tabId === currentTabId && changeInfo.status === 'loading') {
      await loadState(currentTabId);
    }
  });

  // Setup event listeners
  btnReadMore.addEventListener('click', () => {
    const isExpanded = successTextPreview.classList.toggle('expanded');
    btnReadMore.textContent = isExpanded ? 'Thu gọn' : 'Xem thêm';
    btnReadMore.setAttribute('aria-expanded', isExpanded.toString());
  });

  btnCopy.addEventListener('click', handleCopyResult);

  btnRetry.addEventListener('click', async () => {
    if (currentTabId) {
      const key = `tabState_${currentTabId}`;
      const data = await chrome.storage.session.get(key);
      const state = data[key] as TabAnalysisState | undefined;
      
      if (state && state.request) {
        chrome.runtime.sendMessage({
          type: 'ANALYZE_REQUEST',
          payload: state.request,
          tabId: currentTabId
        });
      } else {
        chrome.storage.session.set({ [key]: { status: 'idle' } });
      }
    }
  });
}

async function loadState(tabId: number) {
  const key = `tabState_${tabId}`;
  const data = await chrome.storage.session.get(key);
  const state = data[key] as TabAnalysisState | undefined;
  if (state) {
    renderState(state);
  } else {
    renderState({ status: 'idle' });
  }
}

function hideAllStates() {
  stateIdle.classList.add('hidden');
  stateLoading.classList.add('hidden');
  stateSuccess.classList.add('hidden');
  stateError.classList.add('hidden');
  stopLoadingAnimation();
}

const LOADING_STEPS = [
  'Đang tách ý chính...',
  'Đang tìm kiếm nguồn đối chứng...',
  'Đang đánh giá độ tin cậy...'
];

function startLoadingAnimation() {
  let stepIndex = 0;
  loadingStepText.textContent = LOADING_STEPS[0];
  
  if (loadingInterval) clearInterval(loadingInterval);
  
  loadingInterval = window.setInterval(() => {
    stepIndex = (stepIndex + 1) % LOADING_STEPS.length;
    loadingStepText.textContent = LOADING_STEPS[stepIndex];
  }, 2500);
}

function stopLoadingAnimation() {
  if (loadingInterval) {
    clearInterval(loadingInterval);
    loadingInterval = null;
  }
}

function renderState(state: TabAnalysisState) {
  hideAllStates();

  switch (state.status) {
    case 'idle':
      stateIdle.classList.remove('hidden');
      break;
    
    case 'loading':
      stateLoading.classList.remove('hidden');
      if (state.request?.text) {
        loadingTextPreview.textContent = state.request.text;
      }
      startLoadingAnimation();
      break;

    case 'success':
      stateSuccess.classList.remove('hidden');
      if (state.response) {
        if (state.request?.text) {
          setupTextPreview(state.request.text);
        }
        renderSuccess(state.response);
      }
      break;

    case 'error':
      stateError.classList.remove('hidden');
      errorMessage.textContent = state.error || 'Lỗi không xác định.';
      break;
  }
}

function setupTextPreview(text: string) {
  successTextPreview.textContent = text;
  successTextPreview.classList.remove('expanded');
  btnReadMore.textContent = 'Xem thêm';
  btnReadMore.setAttribute('aria-expanded', 'false');
  
  // Need to check if text needs truncation (approximate logic since scrollHeight is tricky before render)
  if (text.length > 150) {
    btnReadMore.classList.remove('hidden');
  } else {
    btnReadMore.classList.add('hidden');
  }
}

function getVerdictInfo(verdict: string) {
  switch (verdict) {
    case 'Thật': return { class: 'verdict-True', icon: '✅', text: 'Đáng tin cậy' };
    case 'Giả': return { class: 'verdict-False', icon: '❌', text: 'Sai sự thật' };
    case 'Thiếu ngữ cảnh': return { class: 'verdict-Mixed', icon: '⚠️', text: 'Thiếu ngữ cảnh' };
    default: return { class: 'verdict-Unverified', icon: '❓', text: 'Chưa thể xác minh' };
  }
}

function renderSuccess(response: AnalyzeResponse) {
  // Service warning
  if (response.service_status && response.service_status !== 'ok') {
    serviceWarning.classList.remove('hidden');
  } else {
    serviceWarning.classList.add('hidden');
  }

  // Verdict
  const vInfo = getVerdictInfo(response.verdict);
  resultVerdict.className = `verdict-badge ${vInfo.class}`;
  verdictIcon.textContent = vInfo.icon;
  verdictText.textContent = vInfo.text;

  // Confidence
  resultConfidenceText.textContent = `${response.confidence}%`;
  resultConfidenceBar.style.width = `${response.confidence}%`;
  confidenceProgress.setAttribute('aria-valuenow', response.confidence.toString());

  // Explanation
  resultExplanation.textContent = response.explanation;

  // Sources
  resultSources.textContent = ''; // Clear existing
  if (response.sources && response.sources.length > 0) {
    response.sources.forEach(source => {
      const li = document.createElement('li');
      li.className = 'source-item';

      const header = document.createElement('div');
      header.className = 'source-header';

      const publisher = document.createElement('span');
      publisher.className = 'source-publisher';
      publisher.textContent = source.publisher || 'Nguồn bên ngoài';

      header.appendChild(publisher);

      if (source.stance) {
        const stanceBadge = document.createElement('span');
        const sType = source.stance.toLowerCase();
        
        let stanceClass = 'stance-neutral';
        let stanceText = 'Trung lập';
        if (sType.includes('support')) { stanceClass = 'stance-support'; stanceText = 'Ủng hộ'; }
        else if (sType.includes('refute')) { stanceClass = 'stance-refute'; stanceText = 'Bác bỏ'; }
        
        stanceBadge.className = `stance-badge ${stanceClass}`;
        stanceBadge.textContent = stanceText;
        header.appendChild(stanceBadge);
      }

      li.appendChild(header);

      const titleEl = document.createElement('h4');
      titleEl.className = 'source-title';
      const a = document.createElement('a');
      a.href = source.url;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.textContent = source.title || source.url;
      titleEl.appendChild(a);
      li.appendChild(titleEl);

      if (source.snippet) {
        const snippetEl = document.createElement('p');
        snippetEl.className = 'source-snippet';
        snippetEl.textContent = source.snippet;
        li.appendChild(snippetEl);
      }

      resultSources.appendChild(li);
    });
  } else {
    const li = document.createElement('li');
    li.textContent = 'Không tìm thấy nguồn tham khảo độc lập.';
    resultSources.appendChild(li);
  }
}

async function handleCopyResult() {
  try {
    const verdict = verdictText.textContent || '';
    const confidence = resultConfidenceText.textContent || '';
    const explanation = resultExplanation.textContent || '';
    
    let text = `[TrustMeBro] Kết quả kiểm chứng:\n- Kết luận: ${verdict} (${confidence})\n- Giải thích: ${explanation}\n\nNguồn tham khảo:\n`;
    
    const sourceItems = resultSources.querySelectorAll('.source-item');
    if (sourceItems.length > 0) {
      sourceItems.forEach((item, index) => {
        const a = item.querySelector('a');
        text += `${index + 1}. ${a?.textContent} - ${a?.href}\n`;
      });
    } else {
      text += 'Không có nguồn tham khảo.\n';
    }

    text += '\n*Lưu ý: Kết quả do AI tổng hợp, chỉ mang tính tham khảo.*';

    await navigator.clipboard.writeText(text);
    
    const originalText = btnCopy.textContent;
    btnCopy.textContent = '✅ Đã sao chép';
    setTimeout(() => {
      btnCopy.textContent = originalText;
    }, 2000);
  } catch (err) {
    console.error('Failed to copy: ', err);
  }
}

init().catch(console.error);
