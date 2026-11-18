import type { PlatformAdapter, SelectionInfo } from './platform-adapter';

export class FacebookAdapter implements PlatformAdapter {
  id = 'facebook';

  matches(url: URL): boolean {
    return url.hostname.includes('facebook.com');
  }

  getSelectionInfo(): SelectionInfo | null {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return null;

    const text = selection.toString().trim();
    if (!text || text.length < 20 || text.length > 2000) {
      return null;
    }

    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();

    // Validate rect
    if (rect.width === 0 || rect.height === 0) return null;

    return { text, rect };
  }
}
