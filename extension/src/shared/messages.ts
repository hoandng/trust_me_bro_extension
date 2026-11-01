import type { SelectionPayload } from '../features/analysis/types';

export interface AnalyzeRequestMessage {
  type: 'ANALYZE_REQUEST';
  payload: SelectionPayload;
  tabId?: number;
}

export type ExtensionMessage = AnalyzeRequestMessage;

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
