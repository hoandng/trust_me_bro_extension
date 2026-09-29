import { ExtensionMessage } from '../../shared/types';

export class FloatingButton {
  private container: HTMLDivElement | null = null;
  private shadow: ShadowRoot | null = null;
  private selectedText: string = '';
  private platformId: string = '';

  constructor() {
    this.createButton();
  }

  private createButton() {
    this.container = document.createElement('div');
    this.container.style.position = 'absolute';
    this.container.style.zIndex = '999999';
    this.container.style.display = 'none';

    this.shadow = this.container.attachShadow({ mode: 'closed' });

    const btn = document.createElement('button');
    btn.style.display = 'flex';
    btn.style.alignItems = 'center';
    btn.style.gap = '6px';
    btn.style.padding = '6px 6px';
    btn.style.backgroundColor = '#7baef1';
    btn.style.color = '#ffffff';
    btn.style.border = 'none';
    btn.style.borderRadius = '4px';
    btn.style.cursor = 'pointer';
    btn.style.fontSize = '14px';
    btn.style.fontWeight = 'bold';
    btn.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';

    const icon = document.createElement('img');
    icon.src = chrome.runtime.getURL('icons/icon16.png');
    icon.style.width = '16px';
    icon.style.height = '16px';

    btn.appendChild(icon);

    btn.addEventListener('mousedown', (e) => {
      e.stopPropagation(); // Prevent document from hiding the button immediately
    });

    btn.addEventListener('mouseup', (e) => {
      e.stopPropagation(); // Prevent document from re-triggering selection logic
    });

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.handleAnalyze();
    });

    this.shadow.appendChild(btn);
    document.body.appendChild(this.container);
  }

  public show(rect: DOMRect, text: string, platformId: string) {
    if (!this.container) return;

    this.selectedText = text;
    this.platformId = platformId;

    // Positioning slightly above the selection
    this.container.style.top = `${window.scrollY + rect.top - 40}px`;
    this.container.style.left = `${window.scrollX + rect.left + (rect.width / 2) - 45}px`;
    this.container.style.display = 'block';
  }

  public hide() {
    if (this.container && this.container.style.display !== 'none') {
      this.container.style.display = 'none';
      this.selectedText = '';
      this.platformId = '';
    }
  }

  private handleAnalyze() {
    if (!this.selectedText) return;

    const message: ExtensionMessage = {
      type: 'ANALYZE_REQUEST',
      payload: {
        text: this.selectedText,
        platform: this.platformId,
        page_url: window.location.href
      }
    };

    chrome.runtime.sendMessage(message).catch(() => {
      // Ignore errors if background is not ready
    });

    this.hide();
  }
}
