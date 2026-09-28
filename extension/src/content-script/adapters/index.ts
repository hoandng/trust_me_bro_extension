import { PlatformAdapter } from './platform-adapter';
import { FacebookAdapter } from './facebook-adapter';

const adapters: PlatformAdapter[] = [
  new FacebookAdapter()
];

export function getAdapterForUrl(url: URL): PlatformAdapter | null {
  for (const adapter of adapters) {
    if (adapter.matches(url)) {
      return adapter;
    }
  }
  return null;
}
