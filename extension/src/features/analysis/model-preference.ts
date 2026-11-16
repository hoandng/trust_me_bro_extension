import { getSessionValue, setSessionValue } from '../../infrastructure/storage/session-store';

const preferenceKey = 'preferredGeminiModel';
const catalogCacheKey = 'geminiModelCatalog';

export interface ModelCatalog {
  default_model: string;
  models: string[];
}

export async function getPreferredModel(): Promise<string | undefined> {
  const stored = await chrome.storage.local.get(preferenceKey);
  const value = stored[preferenceKey];
  return typeof value === 'string' && value ? value : undefined;
}

export async function savePreferredModel(model: string): Promise<void> {
  await chrome.storage.local.set({ [preferenceKey]: model });
}

export async function getCachedModelCatalog(): Promise<ModelCatalog | undefined> {
  const cached = await getSessionValue<ModelCatalog>(catalogCacheKey);
  if (
    cached &&
    typeof cached === 'object' &&
    typeof cached.default_model === 'string' &&
    Array.isArray(cached.models) &&
    cached.models.every((model) => typeof model === 'string')
  ) {
    return cached;
  }
  return undefined;
}

export async function setCachedModelCatalog(catalog: ModelCatalog): Promise<void> {
  await setSessionValue(catalogCacheKey, catalog);
}
