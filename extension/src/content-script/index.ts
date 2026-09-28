import { getAdapterForUrl } from './adapters';
import { FloatingButton } from './ui/floating-button';

let floatingButton: FloatingButton | null = null;
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

function init() {
  const currentUrl = new URL(window.location.href);
  const adapter = getAdapterForUrl(currentUrl);

  if (!adapter) {
    return; // No adapter for this site
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

  const handleHideEvents = (e: Event) => {
    // If it's a click, and the target is inside our shadow DOM, ignore
    // Note: since our shadow mode is closed, e.target will be the host element.
    if (e.type === 'keydown' && (e as KeyboardEvent).key !== 'Escape') {
      return;
    }
    
    if (e.type === 'mousedown') {
      // If we clicked inside the shadow dom host, don't hide
      // But we can't easily check closed shadow dom, so we rely on mouseup/selectionchange to re-show if needed,
      // or we just let it hide and if selection is still there, mouseup will trigger again.
      // Wait, we should not hide if the selection is active inside our button. But our button is just a button.
      // If the user clicks the button, the click event on the button stops propagation.
    }
    
    if (floatingButton) {
      floatingButton.hide();
    }
  };

  document.addEventListener('selectionchange', handleSelection);
  document.addEventListener('mouseup', handleSelection);
  document.addEventListener('keyup', (e) => {
    if (e.key === 'Escape') {
      handleHideEvents(e);
    } else {
      handleSelection();
    }
  });

  document.addEventListener('mousedown', handleHideEvents);
  document.addEventListener('scroll', handleHideEvents, { passive: true });
}

// Initialize
init();
