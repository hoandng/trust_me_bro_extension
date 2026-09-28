import { ExtensionMessage } from '../shared/types';

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(console.error);

chrome.runtime.onMessage.addListener((message: ExtensionMessage, _sender, _sendResponse) => {
  if (message.type === 'ANALYZE_REQUEST') {
    // DO NOT log the raw text in production for privacy reasons.
    console.log(`[Background] Received ANALYZE_REQUEST from ${message.payload.platform}`);
    console.log(`[Background] Text length: ${message.payload.text.length} chars. URL: ${message.payload.page_url}`);
    
    // Future: Forward to side panel or backend API here
  }
});
