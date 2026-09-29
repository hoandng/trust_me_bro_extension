import { ExtensionMessage, TabAnalysisState } from '../shared/types';

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(console.error);

async function setTabState(tabId: number, state: TabAnalysisState) {
  await chrome.storage.session.set({ [`tabState_${tabId}`]: state });
}

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
const API_KEY = import.meta.env.VITE_EXTENSION_API_KEY || '';

chrome.runtime.onMessage.addListener((message: ExtensionMessage, sender, _sendResponse) => {
  if (message.type === 'ANALYZE_REQUEST') {
    const tabId = message.tabId || sender.tab?.id;
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

    // Actual API call
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    fetch(`${BACKEND_URL}/api/v1/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
      },
      body: JSON.stringify(message.payload),
      signal: controller.signal
    })
    .then(async (res) => {
      clearTimeout(timeoutId);
      if (!res.ok) {
        if (res.status === 401) throw new Error('Lỗi xác thực (401)');
        if (res.status === 422) throw new Error('Dữ liệu không hợp lệ (422)');
        if (res.status === 429) throw new Error('Quá nhiều yêu cầu (429)');
        if (res.status >= 500) throw new Error('Lỗi máy chủ hệ thống (5xx)');
        throw new Error(`Lỗi mạng (${res.status})`);
      }
      return res.json();
    })
    .then((data) => {
      const verdictMap: Record<string, 'Thật' | 'Giả' | 'Thiếu ngữ cảnh' | 'Không thể kiểm chứng'> = {
        'likely_true': 'Thật',
        'likely_false': 'Giả',
        'mixed': 'Thiếu ngữ cảnh',
        'unverified': 'Không thể kiểm chứng'
      };

      const response = {
        verdict: verdictMap[data.verdict] || 'Không thể kiểm chứng',
        confidence: Math.round(data.confidence_score * 100),
        explanation: data.explanation,
        sources: data.sources.map((s: any) => ({ title: s.title, url: s.url }))
      };

      setTabState(tabId, {
        status: 'success',
        request: message.payload,
        response: response as any
      });
    })
    .catch((error) => {
      clearTimeout(timeoutId);
      let errorMessage = error.message || 'Lỗi không xác định';
      if (error.name === 'AbortError' || error.message.includes('fetch')) {
        errorMessage = 'Lỗi kết nối hoặc yêu cầu quá thời gian chờ (30s)';
      }
      setTabState(tabId, {
        status: 'error',
        request: message.payload,
        error: errorMessage
      });
    });
  }
});
