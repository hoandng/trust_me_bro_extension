import {
  getSessionValue,
  setSessionValue,
  subscribeToSessionChanges,
} from '../../infrastructure/storage/session-store';
import type { StoredTabAnalysisState } from './types';
import { isRequestId } from '../../shared/messages';

const keyPrefix = 'tabState_';

export function getTabState(tabId: number): Promise<StoredTabAnalysisState | undefined> {
  return getSessionValue<StoredTabAnalysisState>(`${keyPrefix}${tabId}`);
}

export function setTabState(tabId: number, state: StoredTabAnalysisState): Promise<void> {
  // Chỉ chuyển metadata qua ranh giới storage, kể cả khi caller có thêm dữ liệu.
  const metadata: StoredTabAnalysisState = { status: state.status };
  if (isRequestId(state.request_id)) metadata.request_id = state.request_id;
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
