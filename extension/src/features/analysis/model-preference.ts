const preferenceKey = 'preferredGeminiModel';

export async function getPreferredModel(): Promise<string | undefined> {
  const stored = await chrome.storage.local.get(preferenceKey);
  const value = stored[preferenceKey];
  return typeof value === 'string' && value ? value : undefined;
}

export async function savePreferredModel(model: string): Promise<void> {
  await chrome.storage.local.set({ [preferenceKey]: model });
}
