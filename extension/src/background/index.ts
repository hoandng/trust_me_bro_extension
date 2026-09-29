import { ExtensionMessage, TabAnalysisState } from '../shared/types';
import { getMockResponse } from '../shared/mock';

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(console.error);

async function setTabState(tabId: number, state: TabAnalysisState) {
  await chrome.storage.session.set({ [`tabState_${tabId}`]: state });
}

chrome.runtime.onMessage.addListener((message: ExtensionMessage, sender, _sendResponse) => {
  if (message.type === 'ANALYZE_REQUEST') {
    const tabId = sender.tab?.id;
    if (!tabId) return;

    // Clear previous badge
    chrome.action.setBadgeText({ text: '', tabId }).catch(() => {});

    // DO NOT log the raw text in production for privacy reasons.
    console.log(`[Background] Received ANALYZE_REQUEST from ${message.payload.platform}`);
    console.log(`[Background] Text length: ${message.payload.text.length} chars. URL: ${message.payload.page_url}`);
    
    // Save state as loading
    setTabState(tabId, {
      status: 'loading',
      request: message.payload
    });

    // Enable side panel for this tab
    chrome.sidePanel.setOptions({
      tabId,
      path: 'src/sidepanel/index.html',
      enabled: true
    }).catch(console.error);

    // Try to open side panel programmatically
    chrome.sidePanel.open({ tabId, windowId: sender.tab?.windowId }).catch((error) => {
      console.warn('Failed to open side panel programmatically:', error);
      // Fallback: Notify user to click the action icon via badge
      chrome.action.setBadgeText({ text: '!', tabId });
      chrome.action.setBadgeBackgroundColor({ color: '#dc3545', tabId });
    });

    // Mock API call
    getMockResponse()
      .then((response) => {
        setTabState(tabId, {
          status: 'success',
          request: message.payload,
          response
        });
      })
      .catch((error) => {
        setTabState(tabId, {
          status: 'error',
          request: message.payload,
          error: error.message || 'Lỗi không xác định'
        });
      });
  }
});
