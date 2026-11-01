import type { ExtensionMessage } from '../../../shared/messages';
import { getTabState, setTabState, subscribeToTabStates } from '../state-store';
import { bindAnalysisView, renderAnalysisState } from './render';

export async function initAnalysisPanel(): Promise<void> {
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
