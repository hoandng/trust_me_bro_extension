import {
  getSessionValue,
  setSessionValue,
  subscribeToSessionChanges,
} from '../../infrastructure/storage/session-store';
import type { StoredTabAnalysisState } from './types';

const keyPrefix = 'tabState_';
const uuid4 = /^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/i;

export function getTabState(tabId: number): Promise<StoredTabAnalysisState | undefined> {
  return getSessionValue<StoredTabAnalysisState>(`${keyPrefix}${tabId}`);
}

export function setTabState(tabId: number, state: StoredTabAnalysisState): Promise<void> {
  // Chỉ chuyển metadata qua ranh giới storage, kể cả khi caller có thêm dữ liệu.
  const metadata: StoredTabAnalysisState = { status: state.status };
  if (state.request_id && uuid4.test(state.request_id)) metadata.request_id = state.request_id;
  return setSessionValue(`${keyPrefix}${tabId}`, metadata);
}

export function clearTabState(tabId: number): Promise<void> {
  return chrome.storage.session.remove(`${keyPrefix}${tabId}`);
}

export function subscribeToTabStates(
  listener: (tabId: number, state: StoredTabAnalysisState) => void,
): () => void {
  return subscribeToSessionChanges((changes) => {
    for (const [key, change] of Object.entries(changes)) {
      if (!key.startsWith(keyPrefix)) continue;
      const tabId = Number(key.slice(keyPrefix.length));
      if (Number.isInteger(tabId)) {
        listener(tabId, (change.newValue as StoredTabAnalysisState | undefined) || { status: 'idle' });
      }
    }
  });
}
