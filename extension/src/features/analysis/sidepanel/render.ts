import { renderExplanationSegments } from '../explanation-parser';
import { isFeedbackEndpointEnabled } from '../../../shared/config';
import { buildShareSummary } from '../share-summary';
import type {
  AnalyzeResponse,
  FeedbackRating,
  FeedbackSubmission,
  SourceStance,
  TabAnalysisState,
  VerdictKey,
} from '../types';

const SVG_NS = 'http://www.w3.org/2000/svg';

const VERDICT_SVG_PATHS: Record<VerdictKey, string> = {
  likely_true:
    'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z',
  likely_false:
    'M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z',
  mixed: 'M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z',
  unverified:
    'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z',
};

const STANCE_CLASSES: Record<SourceStance, string> = {
  supports: 'stance-support',
  refutes: 'stance-refute',
  neutral: 'stance-neutral',
};

const LOADING_STEPS = [
  'Đang tách ý chính...',
  'Đang tìm kiếm nguồn đối chứng...',
  'Đang đánh giá độ tin cậy...',
];

let loadingInterval: ReturnType<typeof setInterval> | null = null;
let displayedState: TabAnalysisState = { status: 'idle' };
let activeRequestId: string | undefined;
let selectedRating: FeedbackRating | undefined;
let lastFeedbackState: {
  available: boolean;
  submitted?: FeedbackSubmission;
  sending: boolean;
  error?: string;
} = { available: false, sending: false };

function byId<T extends HTMLElement>(id: string): T {
  return document.getElementById(id) as T;
}

function createVerdictSvg(verdictKey: VerdictKey): SVGSVGElement {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('width', '26');
  svg.setAttribute('height', '26');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');

  const path = document.createElementNS(SVG_NS, 'path');
  path.setAttribute('fill', 'currentColor');
  path.setAttribute('d', VERDICT_SVG_PATHS[verdictKey] ?? VERDICT_SVG_PATHS.unverified);
  svg.appendChild(path);
  return svg;
}

function startLoadingAnimation() {
  const loadingStepText = byId<HTMLParagraphElement>('loading-step-text');
  let stepIndex = 0;
  loadingStepText.textContent = LOADING_STEPS[0];

  if (loadingInterval) clearInterval(loadingInterval);

  loadingInterval = setInterval(() => {
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

function hideAllStates() {
  byId('state-idle').classList.add('hidden');
  byId('state-loading').classList.add('hidden');
  byId('state-success').classList.add('hidden');
  byId('state-error').classList.add('hidden');
  stopLoadingAnimation();
}

export function renderAnalysisState(state: TabAnalysisState) {
  displayedState = state;
  byId<HTMLParagraphElement>('copy-status').textContent = '';
  hideAllStates();

  switch (state.status) {
    case 'idle':
      byId('state-idle').classList.remove('hidden');
      break;

    case 'loading':
      byId('state-loading').classList.remove('hidden');
      byId('loading-text-preview').textContent = state.request?.text ?? '';
      startLoadingAnimation();
      break;

    case 'success':
      byId('state-success').classList.remove('hidden');
      if (state.response) {
        if (state.response.request_id !== activeRequestId) {
          activeRequestId = state.response.request_id;
          selectedRating = state.feedback?.rating;
          const commentEl = byId<HTMLTextAreaElement>('feedback-comment');
          if (commentEl) commentEl.value = state.feedback?.comment ?? '';
        }
        setupTextPreview(state.request?.text ?? '');
        renderSuccess(state.response);
      }
      break;

    case 'error':
      byId('state-error').classList.remove('hidden');
      byId<HTMLParagraphElement>('error-message').textContent = state.error || 'Lỗi không xác định.';
      break;
  }
}

function updateStarButtons(locked: boolean) {
  const container = byId<HTMLDivElement>('feedback-stars');
  const buttons = container.querySelectorAll<HTMLButtonElement>('.star-btn');
  buttons.forEach((btn) => {
    const rating = Number(btn.dataset.rating) as FeedbackRating;
    const isPressed = selectedRating === rating;
    const isHighlighted = selectedRating !== undefined && rating <= selectedRating;
    btn.setAttribute('aria-pressed', String(isPressed));
    btn.classList.toggle('star-active', isHighlighted);
    btn.disabled = locked;
  });
}

export function renderFeedbackState(
  available: boolean,
  submitted: FeedbackSubmission | undefined,
  sending: boolean,
  error?: string,
) {
  lastFeedbackState = { available, submitted, sending, error };
  const feedbackActions = byId<HTMLElement>('feedback-actions');
  const commentEl = byId<HTMLTextAreaElement>('feedback-comment');
  const submitBtn = byId<HTMLButtonElement>('btn-submit-feedback');
  const feedbackStatus = byId<HTMLParagraphElement>('feedback-status');

  feedbackActions.classList.toggle('hidden', !available);
  if (!available) return;

  const endpointEnabled = isFeedbackEndpointEnabled();
  if (!endpointEnabled) {
    updateStarButtons(false);
    commentEl.disabled = false;
    submitBtn.disabled = true;
    feedbackStatus.textContent = 'Tính năng đánh giá sẽ sớm có';
    return;
  }

  if (submitted) {
    selectedRating = submitted.rating;
    if (submitted.comment !== undefined) {
      commentEl.value = submitted.comment;
    }
  }

  const locked = sending || submitted !== undefined;
  updateStarButtons(locked);
  commentEl.disabled = locked;
  submitBtn.disabled = locked || selectedRating === undefined;

  if (error) {
    feedbackStatus.textContent = error;
  } else if (sending) {
    feedbackStatus.textContent = 'Đang gửi đánh giá…';
  } else if (submitted) {
    feedbackStatus.textContent = 'Cảm ơn bạn';
  } else {
    feedbackStatus.textContent = '';
  }
}

function setupTextPreview(text: string) {
  const successTextPreview = byId<HTMLParagraphElement>('success-text-preview');
  const btnReadMore = byId<HTMLButtonElement>('btn-read-more');

  successTextPreview.textContent = text;
  successTextPreview.classList.remove('expanded');
  btnReadMore.textContent = 'Xem thêm';
  btnReadMore.setAttribute('aria-expanded', 'false');

  if (text.length > 150) {
    btnReadMore.classList.remove('hidden');
  } else {
    btnReadMore.classList.add('hidden');
  }
}

function renderSuccess(response: AnalyzeResponse) {
  // 2. Verdict banner
  const resultVerdict = byId<HTMLDivElement>('result-verdict');
  const verdictIcon = byId<HTMLSpanElement>('verdict-icon');
  const verdictText = byId<HTMLHeadingElement>('verdict-text');
  const verdictSubtext = byId<HTMLParagraphElement>('verdict-subtext');

  const verdictKey: VerdictKey = response.verdict_key || 'unverified';
  resultVerdict.className = `verdict-banner verdict-${verdictKey}`;
  verdictIcon.replaceChildren(createVerdictSvg(verdictKey));
  verdictText.textContent = response.conclusion;

  if (response.subtext) {
    verdictSubtext.textContent = response.subtext;
    verdictSubtext.classList.remove('hidden');
  } else {
    verdictSubtext.textContent = '';
    verdictSubtext.classList.add('hidden');
  }

  // Service warning
  const serviceWarning = byId<HTMLDivElement>('service-warning');
  if (response.service_status && response.service_status !== 'ok') {
    serviceWarning.classList.remove('hidden');
  } else {
    serviceWarning.classList.add('hidden');
  }

  // 4. Explanation + Certainty 3-bars (no percentage)
  const resultConfidenceText = byId<HTMLElement>('result-confidence-text');
  resultConfidenceText.textContent = response.confidence_level;

  const barsContainer = byId<HTMLDivElement>('confidence-bars');
  const bars = barsContainer.querySelectorAll<HTMLElement>('.certainty-bar');
  bars.forEach((bar, index) => {
    bar.classList.toggle('active', index < response.confidence_bars);
  });

  const resultExplanation = byId<HTMLParagraphElement>('result-explanation');
  renderExplanationSegments(resultExplanation, response.explanation, document);

  // 5. Sources (n)
  const sources = response.sources || [];
  const sourcesHeading = byId<HTMLElement>('sources-heading');
  sourcesHeading.textContent = `Nguồn liên quan (${sources.length})`;

  const neutralNote = byId<HTMLParagraphElement>('sources-neutral-note');
  neutralNote.classList.toggle('hidden', !response.all_sources_neutral);

  const resultSources = byId<HTMLUListElement>('result-sources');
  resultSources.replaceChildren();

  if (sources.length > 0) {
    sources.forEach((source) => {
      const li = document.createElement('li');
      li.className = 'source-item';

      const header = document.createElement('div');
      header.className = 'source-header';

      const sourceDetails = document.createElement('div');
      sourceDetails.className = 'source-meta';

      const publisher = document.createElement('span');
      publisher.className = 'source-publisher';
      publisher.textContent = source.publisher || 'Nguồn bên ngoài';
      sourceDetails.appendChild(publisher);

      if (source.publishedDate) {
        const date = document.createElement('span');
        date.className = 'source-date';
        date.textContent = `· ${source.publishedDate}`;
        sourceDetails.appendChild(date);
      }
      header.appendChild(sourceDetails);

      const stanceBadge = document.createElement('span');
      const stanceClass = STANCE_CLASSES[source.stance] ?? 'stance-neutral';
      stanceBadge.className = `stance-badge ${stanceClass}`;
      stanceBadge.textContent = source.stanceLabel || 'Liên quan';
      header.appendChild(stanceBadge);

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
    li.className = 'source-item';
    li.textContent = 'Không tìm thấy nguồn tham khảo độc lập.';
    resultSources.appendChild(li);
  }

  // 9. Technical details (Model, Response time, Analyzed text)
  const usage = response.model_usage;
  const modelInfo = byId<HTMLParagraphElement>('model-usage');
  if (usage) {
    const models = [
      usage.extraction_model && `Trích xuất: ${usage.extraction_model}`,
      usage.assessment_model && `Đánh giá: ${usage.assessment_model}`,
    ].filter(Boolean);
    modelInfo.textContent = `Ưu tiên: ${usage.requested_model}${models.length ? ` · ${models.join(' · ')}` : ''}${
      usage.fallbacks.length ? ' (Đã tự chuyển model khi chạm hạn mức)' : ''
    }`;
  } else {
    modelInfo.textContent = 'Mặc định hệ thống';
  }

  const durationEl = byId<HTMLParagraphElement>('response-duration');
  if (typeof response.duration_ms === 'number' && Number.isFinite(response.duration_ms)) {
    durationEl.textContent = `${response.duration_ms} ms`;
  } else {
    durationEl.textContent = 'Không có dữ liệu';
  }
}

async function handleCopyResult() {
  const state = displayedState;
  const copyStatus = byId<HTMLParagraphElement>('copy-status');
  if (state.status !== 'success' || !state.response) return;
  try {
    await navigator.clipboard.writeText(buildShareSummary(state.response, state.request));
    if (displayedState === state) copyStatus.textContent = 'Đã sao chép bản tóm tắt.';
  } catch {
    if (displayedState === state) copyStatus.textContent = 'Chưa sao chép được. Hãy thử lại.';
  }
}

export function bindAnalysisView(
  onRetry: () => void,
  onFeedback: (rating: FeedbackRating, comment?: string) => void,
  onToggleSettings?: (open: boolean) => void,
) {
  const btnReadMore = byId<HTMLButtonElement>('btn-read-more');
  const successTextPreview = byId<HTMLParagraphElement>('success-text-preview');
  const btnCopy = byId<HTMLButtonElement>('btn-copy');
  const btnRetry = byId<HTMLButtonElement>('btn-retry');
  const btnSettings = byId<HTMLButtonElement>('btn-settings');
  const settingsPanel = byId<HTMLElement>('settings-panel');
  const starsContainer = byId<HTMLDivElement>('feedback-stars');
  const submitBtn = byId<HTMLButtonElement>('btn-submit-feedback');
  const commentEl = byId<HTMLTextAreaElement>('feedback-comment');

  btnReadMore.addEventListener('click', () => {
    const isExpanded = successTextPreview.classList.toggle('expanded');
    btnReadMore.textContent = isExpanded ? 'Thu gọn' : 'Xem thêm';
    btnReadMore.setAttribute('aria-expanded', isExpanded.toString());
  });

  btnCopy.addEventListener('click', () => {
    void handleCopyResult();
  });

  btnRetry.addEventListener('click', onRetry);

  btnSettings.addEventListener('click', () => {
    const isHidden = settingsPanel.classList.toggle('hidden');
    const isOpen = !isHidden;
    btnSettings.setAttribute('aria-expanded', String(isOpen));
    onToggleSettings?.(isOpen);
  });

  starsContainer.querySelectorAll<HTMLButtonElement>('.star-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const rating = Number(btn.dataset.rating);
      if (rating >= 1 && rating <= 5) {
        selectedRating = rating as FeedbackRating;
        renderFeedbackState(
          lastFeedbackState.available,
          lastFeedbackState.submitted,
          lastFeedbackState.sending,
           undefined,
        );
      }
    });
  });

  submitBtn.addEventListener('click', () => {
    if (selectedRating === undefined || !isFeedbackEndpointEnabled()) return;
    const comment = commentEl.value.trim();
    onFeedback(selectedRating, comment || undefined);
  });

  window.addEventListener('pagehide', stopLoadingAnimation);
}
