import type { FeedbackSubmission, SelectionPayload } from '../features/analysis/types';

export interface AnalyzeRequestMessage {
  type: 'ANALYZE_REQUEST';
  payload: SelectionPayload;
  tabId?: number;
}

export interface AnalysisTabMessage {
  type: 'GET_ANALYSIS_STATE' | 'RETRY_ANALYSIS';
  tabId: number;
}

export interface SubmitFeedbackMessage extends FeedbackSubmission {
  type: 'SUBMIT_ANALYSIS_FEEDBACK';
  tabId: number;
}

export type ExtensionMessage = AnalyzeRequestMessage | AnalysisTabMessage | SubmitFeedbackMessage;

export function isRequestId(value: unknown): value is string {
  return typeof value === 'string' &&
    /^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/i.test(value);
}

function isTabId(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}

export function isSubmitFeedbackMessage(message: unknown): message is SubmitFeedbackMessage {
  return !!message && typeof message === 'object' &&
    'type' in message && message.type === 'SUBMIT_ANALYSIS_FEEDBACK' &&
    'tabId' in message && isTabId(message.tabId) &&
    'request_id' in message && isRequestId(message.request_id) &&
    'helpful' in message && typeof message.helpful === 'boolean';
}

export function isAnalysisTabMessage(message: unknown): message is AnalysisTabMessage {
  return !!message && typeof message === 'object' &&
    'type' in message && (message.type === 'GET_ANALYSIS_STATE' || message.type === 'RETRY_ANALYSIS') &&
    'tabId' in message && isTabId(message.tabId);
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
