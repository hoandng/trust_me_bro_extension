import type { AnalyzeRequestMessage } from '../../../shared/messages';
import { SIDEPANEL_PATH } from '../../../shared/config';
import { analyzeSelection } from './analysis-api';
import { getPreferredModel } from '../model-preference';
import { setTabState } from '../state-store';

export async function handleAnalysisRequest(
  message: AnalyzeRequestMessage,
  sender: chrome.runtime.MessageSender,
): Promise<void> {
  const tabId = message.tabId ?? sender.tab?.id;
  if (tabId === undefined) return;

  // Gọi ngay trong message handler để giữ user gesture khi mở panel.
  chrome.sidePanel.open({ tabId }).catch((error: unknown) => {
    console.warn('[Analysis] Unable to open side panel:', error);
    chrome.action.setBadgeText({ text: '!', tabId }).catch(console.error);
    chrome.action.setBadgeBackgroundColor({ color: '#dc3545', tabId }).catch(console.error);
  });
  chrome.sidePanel.setOptions({ tabId, path: SIDEPANEL_PATH, enabled: true }).catch(console.error);
  chrome.action.setBadgeText({ text: '', tabId }).catch(console.error);

  console.debug('[Analysis] Request received', {
    platform: message.payload.platform,
    textLength: message.payload.text.length,
  });

  // Snapshot the preference once; changing the selector does not alter an active request.
  let payload = message.payload;
  try {
    const model = await getPreferredModel();
    payload = { ...message.payload };
    delete payload.model_id;
    if (model) payload.model_id = model;
    await setTabState(tabId, { status: 'loading', request: payload });
    const response = await analyzeSelection(payload);
    await setTabState(tabId, { status: 'success', request: payload, response });
  } catch (error) {
    await setTabState(tabId, {
      status: 'error',
      request: payload,
      error: error instanceof Error ? error.message : 'Lỗi không xác định',
    });
  }
}
