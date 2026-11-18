import { getFromBackend } from '../../../infrastructure/api/backend-client';
import {
  getCachedModelCatalog,
  getPreferredModel,
  savePreferredModel,
  setCachedModelCatalog,
} from '../model-preference';
import type { ModelCatalog } from '../model-preference';
import { isFeedbackEndpointEnabled } from '../../../shared/config';
import { isRequestId } from '../../../shared/messages';
import type { AnalysisTabMessage, SubmitFeedbackMessage } from '../../../shared/messages';
import { subscribeToTabStates } from '../state-store';
import type { FeedbackRating, FeedbackReply, TabAnalysisState } from '../types';
import { bindAnalysisView, renderAnalysisState, renderFeedbackState } from './render';

export async function initAnalysisPanel(): Promise<void> {
  let currentTabId: number | undefined;
  let loadVersion = 0;
  let currentState: TabAnalysisState = { status: 'idle' };
  const pendingFeedback = new Set<string>();
  let modelSelectorLoaded = false;
  let modelSelectorLoading = false;
  let modelChangeBound = false;

  function refreshFeedback(error?: string) {
    const id = currentState.status === 'success' ? currentState.response?.request_id : undefined;
    const available = isRequestId(id);
    renderFeedbackState(
      available,
      currentState.feedback,
      available && pendingFeedback.has(id),
      error,
    );
  }

  function showState(state: TabAnalysisState) {
    currentState = state;
    renderAnalysisState(state);
    refreshFeedback();
  }

  async function loadState(tabId: number) {
    const version = ++loadVersion;
    const message: AnalysisTabMessage = { type: 'GET_ANALYSIS_STATE', tabId };
    const state = (await chrome.runtime.sendMessage(message)) as TabAnalysisState | undefined;
    // Bỏ qua dữ liệu trả về muộn nếu người dùng đã đổi tab.
    if (tabId === currentTabId && version === loadVersion) {
      showState(state || { status: 'idle' });
    }
  }

  const unsubscribe = subscribeToTabStates((tabId) => {
    if (tabId === currentTabId) void loadState(tabId).catch(console.error);
  });
  window.addEventListener('pagehide', unsubscribe);

  chrome.tabs.onActivated.addListener((activeInfo) => {
    currentTabId = activeInfo.tabId;
    showState({ status: 'idle' });
    void loadState(currentTabId).catch(console.error);
  });
  chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (tabId === currentTabId && changeInfo.status === 'loading') {
      void loadState(tabId).catch(console.error);
    }
  });

  async function ensureModelSelectorLoaded(): Promise<void> {
    if (modelSelectorLoaded || modelSelectorLoading) return;
    modelSelectorLoading = true;
    const selector = document.getElementById('model-selector') as HTMLSelectElement;
    const hint = document.getElementById('model-hint') as HTMLParagraphElement;
    hint.textContent = 'Đang tải danh sách model...';

    try {
      let catalog = await getCachedModelCatalog();
      if (!catalog) {
        catalog = await getFromBackend<ModelCatalog>('/api/v1/models');
        await setCachedModelCatalog(catalog);
      }
      const preferred = await getPreferredModel();
      const saved = preferred && catalog.models.includes(preferred) ? preferred : '';
      if (preferred && !saved) await savePreferredModel('');

      selector.replaceChildren();
      const defaultOption = new Option(`Mặc định (${catalog.default_model})`, '');
      selector.add(defaultOption);
      for (const model of catalog.models) {
        selector.add(new Option(model, model));
      }
      selector.value = saved;
      selector.disabled = false;
      modelSelectorLoaded = true;
      hint.textContent = 'Áp dụng cho lần phân tích tiếp theo. Tự chuyển model khi chạm hạn mức.';

      if (!modelChangeBound) {
        modelChangeBound = true;
        selector.addEventListener('change', () => {
          selector.disabled = true;
          void savePreferredModel(selector.value)
            .then(() => {
              hint.textContent = 'Đã lưu. Áp dụng cho lần phân tích tiếp theo.';
            })
            .catch(() => {
              hint.textContent = 'Không lưu được lựa chọn. Vui lòng thử lại.';
            })
            .finally(() => {
              selector.disabled = false;
            });
        });
      }
    } catch {
      hint.textContent = 'Không tải được danh sách model. Lựa chọn đã lưu vẫn được giữ.';
    } finally {
      modelSelectorLoading = false;
    }
  }

  bindAnalysisView(
    () => {
      void retryAnalysis().catch(console.error);
    },
    (rating, comment) => {
      void submitFeedback(rating, comment);
    },
    (open) => {
      if (open) {
        void ensureModelSelectorLoaded();
      }
    },
  );

  async function submitFeedback(rating: FeedbackRating, comment?: string) {
    if (!isFeedbackEndpointEnabled()) {
      refreshFeedback('Tính năng đánh giá sẽ sớm có');
      return;
    }

    const tabId = currentTabId;
    const id = currentState.response?.request_id;
    if (
      tabId === undefined ||
      currentState.status !== 'success' ||
      !isRequestId(id) ||
      pendingFeedback.has(id) ||
      currentState.feedback !== undefined
    ) {
      return;
    }

    const trimmedComment = comment?.trim();
    const message: SubmitFeedbackMessage = {
      type: 'SUBMIT_ANALYSIS_FEEDBACK',
      tabId,
      request_id: id,
      rating,
      ...(trimmedComment ? { comment: trimmedComment } : {}),
    };
    pendingFeedback.add(id);
    refreshFeedback();
    let reply: FeedbackReply | undefined;
    try {
      reply = (await chrome.runtime.sendMessage(message)) as FeedbackReply | undefined;
    } catch {
      // Khi worker không phản hồi, hiển thị lỗi cho đúng kết quả bên dưới.
    } finally {
      pendingFeedback.delete(id);
    }

    if (currentTabId !== tabId || currentState.response?.request_id !== id) return;
    if (reply?.ok) {
      currentState.feedback = {
        request_id: id,
        rating,
        ...(trimmedComment ? { comment: trimmedComment } : {}),
      };
      void loadState(tabId).catch(() => {
        // Phản hồi đã được gửi, giữ xác nhận nếu lần đọc lại trạng thái thất bại.
      });
    }
    refreshFeedback(
      reply?.ok ? undefined : (reply?.error ?? 'Chưa gửi được phản hồi. Hãy thử lại sau.'),
    );
  }

  async function retryAnalysis() {
    const tabId = currentTabId;
    if (tabId === undefined) return;
    const message: AnalysisTabMessage = { type: 'RETRY_ANALYSIS', tabId };
    await chrome.runtime.sendMessage(message);
    if (tabId === currentTabId) await loadState(tabId);
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  currentTabId ??= tab?.id;
  if (currentTabId !== undefined) {
    await loadState(currentTabId);
    chrome.action.setBadgeText({ text: '', tabId: currentTabId }).catch(console.error);
  } else {
    showState({ status: 'idle' });
  }
}
