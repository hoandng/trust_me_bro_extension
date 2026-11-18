import { getAdapterForUrl } from './adapters';
import { FloatingButton } from './ui/floating-button';

let floatingButton: FloatingButton | null = null;
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

export function initSelectionController() {
  const currentUrl = new URL(window.location.href);
  const adapter = getAdapterForUrl(currentUrl);

  if (!adapter) {
    return; // No adapter for this site
  }

  if (adapter.init) {
    adapter.init();
  }

  floatingButton = new FloatingButton();

  const handleSelection = () => {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const selectionInfo = adapter.getSelectionInfo();
      if (selectionInfo && floatingButton) {
        floatingButton.show(selectionInfo.rect, selectionInfo.text, adapter.id);
      } else if (floatingButton) {
        floatingButton.hide();
      }
    }, 150);
  };

  const handleHideEvents = () => {
    if (floatingButton) {
      floatingButton.hide();
    }
  };

  document.addEventListener('selectionchange', handleSelection);
  document.addEventListener('mouseup', handleSelection);
  document.addEventListener('keyup', (e) => {
    if (e.key === 'Escape') {
      handleHideEvents();
    } else {
      handleSelection();
    }
  });

  document.addEventListener('mousedown', handleHideEvents);
  document.addEventListener('scroll', handleHideEvents, { passive: true });
}
