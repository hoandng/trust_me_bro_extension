import {
  forgetAnalysisTab, getLiveAnalysisState, handleAnalysisRequest, retryAnalysisForTab,
} from '../features/analysis/background/handle-analysis';
import { isAnalysisTabMessage, isAnalyzeRequest } from '../shared/messages';
import { SIDEPANEL_PATH } from '../shared/config';

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(console.error);

chrome.tabs.onRemoved.addListener((tabId) => {
  void forgetAnalysisTab(tabId).catch(() => console.error('[Analysis] Unable to clear tab state'));
});
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === 'loading' || changeInfo.url !== undefined) {
    void forgetAnalysisTab(tabId).catch(() => console.error('[Analysis] Unable to clear tab state'));
  }
});

chrome.runtime.onMessage.addListener((message: unknown, sender, sendResponse) => {
  if (isAnalysisTabMessage(message) && sender.url === chrome.runtime.getURL(SIDEPANEL_PATH)) {
    if (message.type === 'GET_ANALYSIS_STATE') {
      sendResponse(getLiveAnalysisState(message.tabId) ?? { status: 'idle' });
      return;
    }
    void retryAnalysisForTab(message.tabId).then(
      () => sendResponse({ ok: true }),
      () => sendResponse({ ok: false }),
    );
    return true;
  }
  if (isAnalyzeRequest(message)) {
    void handleAnalysisRequest(message, sender).then(
      () => sendResponse({ ok: true }),
      () => {
        console.error('[Analysis] Request failed');
        sendResponse({ ok: false });
      },
    );
    return true;
  }
});
