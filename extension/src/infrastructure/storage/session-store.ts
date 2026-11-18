export async function getSessionValue<T>(key: string): Promise<T | undefined> {
  const data = await chrome.storage.session.get(key);
  return data[key] as T | undefined;
}

export async function setSessionValue<T>(key: string, value: T): Promise<void> {
  await chrome.storage.session.set({ [key]: value });
}

export function subscribeToSessionChanges(
  listener: (changes: Record<string, chrome.storage.StorageChange>) => void,
): () => void {
  chrome.storage.session.onChanged.addListener(listener);
  return () => chrome.storage.session.onChanged.removeListener(listener);
}
