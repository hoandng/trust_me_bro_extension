import type { SelectionPayload } from '../features/analysis/types';

export interface AnalyzeRequestMessage {
  type: 'ANALYZE_REQUEST';
  payload: SelectionPayload;
  tabId?: number;
}

export interface AnalysisTabMessage {
  type: 'GET_ANALYSIS_STATE' | 'RETRY_ANALYSIS';
  tabId: number;
}

export type ExtensionMessage = AnalyzeRequestMessage | AnalysisTabMessage;

export function isAnalysisTabMessage(message: unknown): message is AnalysisTabMessage {
  return !!message && typeof message === 'object' &&
    'type' in message && (message.type === 'GET_ANALYSIS_STATE' || message.type === 'RETRY_ANALYSIS') &&
    'tabId' in message && typeof message.tabId === 'number' &&
    Number.isSafeInteger(message.tabId) && message.tabId >= 0;
}

export function isAnalyzeRequest(message: unknown): message is AnalyzeRequestMessage {
  if (!message || typeof message !== 'object' || !('type' in message)) return false;
  if (message.type !== 'ANALYZE_REQUEST' || !('payload' in message)) return false;

  const payload = message.payload;
  return (
    !!payload &&
    typeof payload === 'object' &&
    'text' in payload &&
    typeof payload.text === 'string' &&
    'platform' in payload &&
    typeof payload.platform === 'string' &&
    'page_url' in payload &&
    typeof payload.page_url === 'string' &&
    (!('tabId' in message) ||
      (typeof message.tabId === 'number' && Number.isInteger(message.tabId)))
  );
}
