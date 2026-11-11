import type { AnalyzeRequestMessage } from '../../../shared/messages';
import { SIDEPANEL_PATH } from '../../../shared/config';
import { analyzeSelection } from './analysis-api';
import { getPreferredModel } from '../model-preference';
import { clearTabState, setTabState } from '../state-store';
import type { TabAnalysisState } from '../types';

// Nội dung thử lại và kết quả có thể chứa nguyên văn bài đăng. Chỉ giữ trong RAM.
const tabRuns = new Map<number, { state: TabAnalysisState }>();

export function getLiveAnalysisState(tabId: number): TabAnalysisState | undefined {
  return tabRuns.get(tabId)?.state;
}

export async function forgetAnalysisTab(tabId: number): Promise<void> {
  tabRuns.delete(tabId);
  await clearTabState(tabId);
}

export async function retryAnalysisForTab(tabId: number): Promise<void> {
  const request = getLiveAnalysisState(tabId)?.request;
  if (request) {
    await handleAnalysisRequest({ type: 'ANALYZE_REQUEST', payload: request, tabId }, {});
  } else {
    await forgetAnalysisTab(tabId);
  }
}

export async function handleAnalysisRequest(
  message: AnalyzeRequestMessage,
  sender: chrome.runtime.MessageSender,
): Promise<void> {
  const tabId = message.tabId ?? sender.tab?.id;
  if (tabId === undefined) return;
  const run: { state: TabAnalysisState } = {
    state: { status: 'loading', request: message.payload },
  };
  tabRuns.set(tabId, run);

  const publish = async (state: TabAnalysisState) => {
    if (tabRuns.get(tabId) !== run) return;
    run.state = state;
    await setTabState(tabId, { status: state.status, request_id: state.response?.request_id });
  };

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
    await publish(run.state);
    const model = await getPreferredModel();
    if (tabRuns.get(tabId) !== run) return;
    payload = { ...message.payload };
    delete payload.model_id;
    if (model) payload.model_id = model;
    const response = await analyzeSelection(payload);
    await publish({ status: 'success', request: payload, response });
  } catch (error) {
    await publish({
      status: 'error',
      request: payload,
      error: error instanceof Error ? error.message : 'Lỗi không xác định',
    });
  }
}
