import { buildShareSummary } from '../share-summary';
import type { TabAnalysisState, AnalyzeResponse } from '../types';

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
const verdictText = document.getElementById('verdict-text') as HTMLHeadingElement;

const resultConfidenceText = document.getElementById('result-confidence-text') as HTMLSpanElement;
const resultConfidenceBar = document.getElementById('result-confidence-bar') as HTMLDivElement;
const confidenceProgress = document.getElementById('confidence-progress') as HTMLDivElement;

const resultExplanation = document.getElementById('result-explanation') as HTMLParagraphElement;
const resultSources = document.getElementById('result-sources') as HTMLUListElement;

const errorMessage = document.getElementById('error-message') as HTMLParagraphElement;
const btnRetry = document.getElementById('btn-retry') as HTMLButtonElement;
const btnCopy = document.getElementById('btn-copy') as HTMLButtonElement;
const copyStatus = document.getElementById('copy-status') as HTMLParagraphElement;
const feedbackActions = document.getElementById('feedback-actions') as HTMLDivElement;
const btnHelpful = document.getElementById('btn-helpful') as HTMLButtonElement;
const btnNotHelpful = document.getElementById('btn-not-helpful') as HTMLButtonElement;
const feedbackStatus = document.getElementById('feedback-status') as HTMLParagraphElement;

let loadingInterval: number | null = null;
let displayedState: TabAnalysisState = { status: 'idle' };

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
  'Đang đánh giá độ tin cậy...',
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

export function renderAnalysisState(state: TabAnalysisState) {
  displayedState = state;
  copyStatus.textContent = '';
  hideAllStates();

  switch (state.status) {
    case 'idle':
      stateIdle.classList.remove('hidden');
      break;

    case 'loading':
      stateLoading.classList.remove('hidden');
      loadingTextPreview.textContent = state.request?.text ?? '';
      startLoadingAnimation();
      break;

    case 'success':
      stateSuccess.classList.remove('hidden');
      if (state.response) {
        setupTextPreview(state.request?.text ?? '');
        renderSuccess(state.response);
      }
      break;

    case 'error':
      stateError.classList.remove('hidden');
      errorMessage.textContent = state.error || 'Lỗi không xác định.';
      break;
  }
}

export function renderFeedbackState(
  available: boolean, selected: boolean | undefined, sending: boolean, error?: string,
) {
  feedbackActions.classList.toggle('hidden', !available);
  btnHelpful.disabled = !available || sending || selected === true;
  btnNotHelpful.disabled = !available || sending || selected === false;
  btnHelpful.setAttribute('aria-pressed', String(selected === true));
  btnNotHelpful.setAttribute('aria-pressed', String(selected === false));
  feedbackStatus.textContent = error ?? (sending
    ? 'Đang gửi phản hồi…'
    : selected !== undefined ? 'Đã gửi phản hồi. Cảm ơn bạn!' : '');
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
    case 'Thật':
      return { class: 'verdict-True', icon: '✅' };
    case 'Giả':
      return { class: 'verdict-False', icon: '❌' };
    case 'Thiếu ngữ cảnh':
      return { class: 'verdict-Mixed', icon: '⚠️' };
    default:
      return { class: 'verdict-Unverified', icon: '❓' };
  }
}

const stanceLabels = {
  supports: { className: 'stance-support', label: 'Đồng tình' },
  refutes: { className: 'stance-refute', label: 'Phản bác' },
  neutral: { className: 'stance-neutral', label: 'Trung lập' },
};

function renderSuccess(response: AnalyzeResponse) {
  const usage = response.model_usage;
  const modelInfo = document.getElementById('model-usage') as HTMLParagraphElement;
  modelInfo.classList.toggle('hidden', !usage);
  if (usage) {
    const models = [usage.extraction_model && `Trích xuất: ${usage.extraction_model}`,
      usage.assessment_model && `Đánh giá: ${usage.assessment_model}`].filter(Boolean);
    modelInfo.textContent = `Ưu tiên: ${usage.requested_model}. ${models.join(' · ')}${
      usage.fallbacks.length ? '. Đã tự chuyển hoặc bỏ qua model đang chạm hạn mức.' : ''}`;
  }
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
  verdictText.textContent = response.conclusion;

  // Confidence
  resultConfidenceText.textContent = `${response.confidence}%`;
  resultConfidenceBar.style.width = `${response.confidence}%`;
  confidenceProgress.setAttribute('aria-valuenow', response.confidence.toString());

  // Explanation
  resultExplanation.textContent = response.explanation;

  // Sources
  resultSources.textContent = ''; // Clear existing
  if (response.sources && response.sources.length > 0) {
    response.sources.forEach((source) => {
      const li = document.createElement('li');
      li.className = 'source-item';

      const header = document.createElement('div');
      header.className = 'source-header';

      const sourceDetails = document.createElement('div');
      const publisher = document.createElement('span');
      publisher.className = 'source-publisher';
      publisher.textContent = source.publisher || 'Nguồn bên ngoài';

      sourceDetails.appendChild(publisher);
      if (source.publishedDate) {
        const date = document.createElement('span');
        date.className = 'source-date';
        date.textContent = `Đăng ngày ${source.publishedDate}`;
        sourceDetails.appendChild(date);
      }
      header.appendChild(sourceDetails);

      if (source.stance) {
        const stanceBadge = document.createElement('span');
        const stance = stanceLabels[source.stance];
        stanceBadge.className = `stance-badge ${stance.className}`;
        stanceBadge.textContent = stance.label;
        header.appendChild(stanceBadge);
      }

      li.appendChild(header);

      const titleEl = document.createElement('h4');
      titleEl.className = 'source-title';
      if (source.url) {
        const a = document.createElement('a');
        a.href = source.url;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.textContent = source.title || source.url;
        titleEl.appendChild(a);
      } else {
        titleEl.textContent = source.title || 'Nguồn tham khảo';
      }
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
  const state = displayedState;
  if (state.status !== 'success' || !state.response) return;
  try {
    await navigator.clipboard.writeText(buildShareSummary(state.response, state.request));
    if (displayedState === state) copyStatus.textContent = 'Đã sao chép bản tóm tắt.';
  } catch {
    if (displayedState === state) copyStatus.textContent = 'Chưa sao chép được. Hãy thử lại.';
  }
}

export function bindAnalysisView(onRetry: () => void, onFeedback: (helpful: boolean) => void) {
  btnReadMore.addEventListener('click', () => {
    const isExpanded = successTextPreview.classList.toggle('expanded');
    btnReadMore.textContent = isExpanded ? 'Thu gọn' : 'Xem thêm';
    btnReadMore.setAttribute('aria-expanded', isExpanded.toString());
  });
  btnCopy.addEventListener('click', handleCopyResult);
  btnRetry.addEventListener('click', onRetry);
  btnHelpful.addEventListener('click', () => onFeedback(true));
  btnNotHelpful.addEventListener('click', () => onFeedback(false));
  window.addEventListener('pagehide', stopLoadingAnimation);
}
