import { TabAnalysisState, AnalyzeResponse } from '../shared/types';

// DOM Elements
const stateIdle = document.getElementById('state-idle') as HTMLDivElement;
const stateLoading = document.getElementById('state-loading') as HTMLDivElement;
const stateSuccess = document.getElementById('state-success') as HTMLDivElement;
const stateError = document.getElementById('state-error') as HTMLDivElement;

const loadingTextPreview = document.getElementById('loading-text-preview') as HTMLElement;
const resultVerdict = document.getElementById('result-verdict') as HTMLSpanElement;
const resultConfidenceText = document.getElementById('result-confidence-text') as HTMLSpanElement;
const resultConfidenceBar = document.getElementById('result-confidence-bar') as HTMLDivElement;
const resultExplanation = document.getElementById('result-explanation') as HTMLParagraphElement;
const resultSources = document.getElementById('result-sources') as HTMLUListElement;
const errorMessage = document.getElementById('error-message') as HTMLParagraphElement;
const btnRetry = document.getElementById('btn-retry') as HTMLButtonElement;

let currentTabId: number | null = null;

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
      break;

    case 'success':
      stateSuccess.classList.remove('hidden');
      if (state.response) {
        renderSuccess(state.response);
      }
      break;

    case 'error':
      stateError.classList.remove('hidden');
      errorMessage.textContent = state.error || 'Lỗi không xác định.';
      break;
  }
}

function renderSuccess(response: AnalyzeResponse) {
  // Verdict
  resultVerdict.textContent = response.verdict;
  resultVerdict.className = 'verdict-badge'; // reset
  const verdictClass = `verdict-${response.verdict.replace(/\s+/g, '.')}`;
  resultVerdict.classList.add(verdictClass);

  // Confidence
  resultConfidenceText.textContent = `${response.confidence}%`;
  resultConfidenceBar.style.width = `${response.confidence}%`;

  // Explanation
  resultExplanation.textContent = response.explanation;

  // Sources
  resultSources.innerHTML = ''; // safe as we append text nodes/elements
  if (response.sources && response.sources.length > 0) {
    response.sources.forEach(source => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = source.url;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.textContent = source.title; // safe text rendering
      li.appendChild(a);
      resultSources.appendChild(li);
    });
  } else {
    const li = document.createElement('li');
    li.textContent = 'Không có nguồn tham khảo.';
    resultSources.appendChild(li);
  }
}

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

init().catch(console.error);
