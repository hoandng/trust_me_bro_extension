import {
  getSessionValue,
  setSessionValue,
  subscribeToSessionChanges,
} from '../../infrastructure/storage/session-store';
import type { TabAnalysisState } from './types';

const keyPrefix = 'tabState_';

export function getTabState(tabId: number): Promise<TabAnalysisState | undefined> {
  return getSessionValue<TabAnalysisState>(`${keyPrefix}${tabId}`);
}

export function setTabState(tabId: number, state: TabAnalysisState): Promise<void> {
  return setSessionValue(`${keyPrefix}${tabId}`, state);
}

export function subscribeToTabStates(
  listener: (tabId: number, state: TabAnalysisState) => void,
): () => void {
  return subscribeToSessionChanges((changes) => {
    for (const [key, change] of Object.entries(changes)) {
      if (!key.startsWith(keyPrefix)) continue;
      const tabId = Number(key.slice(keyPrefix.length));
      if (Number.isInteger(tabId)) {
        listener(tabId, (change.newValue as TabAnalysisState | undefined) || { status: 'idle' });
      }
    }
  });
}
