import { getFromBackend } from '../../../infrastructure/api/backend-client';
import { getPreferredModel, savePreferredModel } from '../model-preference';
import type { ExtensionMessage } from '../../../shared/messages';
import { getTabState, setTabState, subscribeToTabStates } from '../state-store';
import { bindAnalysisView, renderAnalysisState } from './render';

export async function initAnalysisPanel(): Promise<void> {
  void initModelSelector();
  let currentTabId: number | undefined;

  async function loadState(tabId: number) {
    const state = await getTabState(tabId);
    // Bỏ qua dữ liệu trả về muộn nếu người dùng đã đổi tab.
    if (tabId === currentTabId) renderAnalysisState(state || { status: 'idle' });
  }

  const unsubscribe = subscribeToTabStates((tabId, state) => {
    if (tabId === currentTabId) renderAnalysisState(state);
  });
  window.addEventListener('pagehide', unsubscribe);

  chrome.tabs.onActivated.addListener((activeInfo) => {
    currentTabId = activeInfo.tabId;
    void loadState(currentTabId).catch(console.error);
  });
  chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (tabId === currentTabId && changeInfo.status === 'loading') {
      void loadState(tabId).catch(console.error);
    }
  });

  bindAnalysisView(() => {
    void retryAnalysis().catch(console.error);
  });

  async function retryAnalysis() {
    const tabId = currentTabId;
    if (tabId === undefined) return;
    const state = await getTabState(tabId);
    if (state?.request) {
      const message: ExtensionMessage = {
        type: 'ANALYZE_REQUEST',
        payload: state.request,
        tabId,
      };
      await chrome.runtime.sendMessage(message);
    } else {
      await setTabState(tabId, { status: 'idle' });
    }
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  currentTabId = tab?.id;
  if (currentTabId !== undefined) {
    await loadState(currentTabId);
    chrome.action.setBadgeText({ text: '', tabId: currentTabId }).catch(console.error);
  } else {
    renderAnalysisState({ status: 'idle' });
  }
}

async function initModelSelector(): Promise<void> {
  const selector = document.getElementById('model-selector') as HTMLSelectElement;
  const hint = document.getElementById('model-hint') as HTMLParagraphElement;
  try {
    const [catalog, preferred] = await Promise.all([
      getFromBackend<{ default_model: string; models: string[] }>('/api/v1/models'),
      getPreferredModel(),
    ]);
    const saved = preferred && catalog.models.includes(preferred) ? preferred : '';
    if (preferred && !saved) await savePreferredModel('');
    selector.replaceChildren();
    const defaultOption = new Option(`Mặc định (${catalog.default_model})`, '');
    selector.add(defaultOption);
    for (const model of catalog.models) selector.add(new Option(model, model));
    selector.value = saved;
    selector.disabled = false;
    hint.textContent = 'Áp dụng cho lần phân tích tiếp theo. Tự chuyển model khi chạm hạn mức.';
    selector.addEventListener('change', () => {
      selector.disabled = true;
      void savePreferredModel(selector.value).then(() => {
        hint.textContent = 'Đã lưu. Áp dụng cho lần phân tích tiếp theo.';
      }).catch(() => {
        hint.textContent = 'Không lưu được lựa chọn. Vui lòng thử lại.';
      }).finally(() => { selector.disabled = false; });
    });
  } catch {
    hint.textContent = 'Không tải được danh sách model. Lựa chọn đã lưu vẫn được giữ.';
  }
}
