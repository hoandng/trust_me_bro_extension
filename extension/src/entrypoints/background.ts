import { handleAnalysisRequest } from '../features/analysis/background/handle-analysis';
import { isAnalyzeRequest } from '../shared/messages';

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(console.error);

chrome.runtime.onMessage.addListener((message: unknown, sender, sendResponse) => {
  if (isAnalyzeRequest(message)) {
    void handleAnalysisRequest(message, sender).then(
      () => sendResponse({ ok: true }),
      (error: unknown) => {
        console.error('[Analysis] Request failed:', error);
        sendResponse({ ok: false });
      },
    );
    return true;
  }
});
