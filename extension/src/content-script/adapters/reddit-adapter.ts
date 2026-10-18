import { ExtensionMessage } from '../../shared/types';
import { PlatformAdapter, SelectionInfo } from './platform-adapter';

export class RedditAdapter implements PlatformAdapter {
  id = 'reddit';

  matches(url: URL): boolean {
    return url.hostname.includes('reddit.com');
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

    if (rect.width === 0 || rect.height === 0) return null;

    return { text, rect };
  }

  init(): void {
    const observerOptions: IntersectionObserverInit = {
      root: null,
      rootMargin: '0px',
      threshold: 0.1
    };

    const postObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          this.processPost(entry.target as HTMLElement);
        }
      });
    }, observerOptions);

    let scanTimeout: ReturnType<typeof setTimeout> | null = null;
    const scanAllPosts = () => {
      document.querySelectorAll('shreddit-post').forEach((post) => {
        postObserver.observe(post);
        if (window.location.pathname.includes('/comments/')) {
          this.processPost(post as HTMLElement);
        }
      });
    };

    const scheduleScan = () => {
      if (scanTimeout) clearTimeout(scanTimeout);
      scanTimeout = setTimeout(scanAllPosts, 150);
    };

    const mutationObserver = new MutationObserver(() => {
      scheduleScan();
    });

    const startTracker = () => {
      scanAllPosts();
      mutationObserver.observe(document.body, { childList: true, subtree: true });
      window.addEventListener('popstate', scheduleScan);
      document.addEventListener('click', () => {
        setTimeout(scanAllPosts, 300);
        setTimeout(scanAllPosts, 800);
      });
      console.log('🚀 Hệ thống Extractor Reddit: Chỉ quét khi bấm vào bài & Hỗ trợ bóc Text!');
    };

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', startTracker);
    } else {
      startTracker();
    }
  }

  private extractPostContent(postElement: HTMLElement): {
    fullContent: string;
    articleUrl: string;
  } {
    let title = '';
    let bodyText = '';
    let articleUrl = '';

    // 1. Bắt Tiêu đề (Title)
    const titleNode = postElement.querySelector('[slot="title"]') as HTMLElement | null;
    if (titleNode) {
      const clone = titleNode.cloneNode(true) as HTMLElement;
      clone.querySelectorAll('[data-tmb-host]').forEach((el) => el.remove());
      title = (clone.innerText || clone.textContent || '').trim();
    }
    if (!title && postElement.getAttribute('post-title')) {
      title = (postElement.getAttribute('post-title') || '').trim();
    }

    // 2. Bắt Thân bài (Body)
    const textBody = postElement.querySelector('[slot="text-body"]') as HTMLElement | null;
    if (textBody && (textBody.innerText || textBody.textContent)) {
      bodyText = (textBody.innerText || textBody.textContent || '').trim();
    } else if (postElement.shadowRoot) {
      const contentNode = (postElement.shadowRoot.querySelector('#-post-rtjson-content') ||
        postElement.shadowRoot.querySelector('div[id*="rtjson"]')) as HTMLElement | null;
      if (contentNode && (contentNode.innerText || contentNode.textContent)) {
        bodyText = (contentNode.innerText || contentNode.textContent || '').trim();
      }
    }

    // 3. Bắt URL bài báo gốc (Nếu có)
    const href = postElement.getAttribute('content-href');
    if (href && href.startsWith('http')) {
      articleUrl = href;
    }

    // Gộp chung Tiêu đề và Thân bài
    const fullContent = [title, bodyText].filter(Boolean).join('\n\n').trim();

    return { fullContent, articleUrl };
  }

  private processPost(postElement: HTMLElement): void {
    // BƯỚC CHẶN: Chỉ cho phép quét nếu đang ở trong trang chi tiết bài viết
    if (!window.location.pathname.includes('/comments/')) {
      return; // Đang ở ngoài Feed thì bỏ qua
    }

    const targetRoot = postElement.shadowRoot || postElement;

    // Chống lặp: Kiểm tra xem nút vẫn còn nằm trong bài viết hay không
    if (
      targetRoot.querySelector('[data-tmb-host]') ||
      postElement.querySelector('[data-tmb-host]')
    ) {
      return;
    }

    const { fullContent, articleUrl } = this.extractPostContent(postElement);

    if (fullContent.length > 10 || articleUrl) {
      postElement.dataset.extracted = 'true';
      postElement.style.border = '2px dashed #7baef1';
      postElement.style.borderRadius = '12px';
      postElement.style.padding = '8px';
      this.injectAnalyzeButton(postElement);
    }
  }

  private injectAnalyzeButton(postElement: HTMLElement): void {
    const host = document.createElement('div');
    host.setAttribute('data-tmb-host', 'true');
    host.style.display = 'flex';
    host.style.alignItems = 'center';
    host.style.justifyContent = 'flex-start';
    host.style.margin = '4px 0 8px 0';
    host.style.zIndex = '9999';

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.title = 'Kiểm chứng bài viết với TrustMeBro';
    btn.style.display = 'inline-flex';
    btn.style.alignItems = 'center';
    btn.style.justifyContent = 'center';
    btn.style.gap = '6px';
    btn.style.padding = '6px 12px';
    btn.style.backgroundColor = '#7baef1';
    btn.style.color = '#ffffff';
    btn.style.border = 'none';
    btn.style.borderRadius = '6px';
    btn.style.cursor = 'pointer';
    btn.style.fontSize = '13px';
    btn.style.fontWeight = '600';
    btn.style.fontFamily = 'system-ui, -apple-system, sans-serif';
    btn.style.boxShadow = '0 2px 6px rgba(0,0,0,0.25)';
    btn.style.transition = 'transform 0.15s ease, background-color 0.15s ease';

    const icon = document.createElement('img');
    icon.src = chrome.runtime.getURL('icons/icon16.png');
    icon.style.width = '18px';
    icon.style.height = '18px';
    icon.style.display = 'block';

    const label = document.createElement('span');
    label.textContent = 'Kiểm chứng bài viết';

    btn.appendChild(icon);
    btn.appendChild(label);

    btn.addEventListener('mouseenter', () => {
      btn.style.backgroundColor = '#5b9bd5';
      btn.style.transform = 'scale(1.03)';
    });

    btn.addEventListener('mouseleave', () => {
      btn.style.backgroundColor = '#7baef1';
      btn.style.transform = 'scale(1)';
    });

    btn.addEventListener('mousedown', (e) => {
      e.stopPropagation();
    });

    btn.addEventListener('mouseup', (e) => {
      e.stopPropagation();
    });

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();

      const { fullContent, articleUrl } = this.extractPostContent(postElement);
      let textToAnalyze = fullContent;

      if (textToAnalyze.length < 20 && articleUrl) {
        textToAnalyze = `${textToAnalyze}\n${articleUrl}`.trim();
      }

      if (textToAnalyze.length < 20) {
        textToAnalyze = textToAnalyze.padEnd(20, ' ');
      } else if (textToAnalyze.length > 2000) {
        textToAnalyze = textToAnalyze.slice(0, 2000);
      }

      console.log('====================================');
      console.log('🟢 NỘI DUNG (TITLE + BODY):\n', fullContent);
      console.log('🔗 LINK BÁO:\n', articleUrl || 'Không có');
      console.log('====================================');

      postElement.style.border = '2px solid #27ae60';

      const message: ExtensionMessage = {
        type: 'ANALYZE_REQUEST',
        payload: {
          text: textToAnalyze,
          platform: this.id,
          page_url: window.location.href
        }
      };

      chrome.runtime.sendMessage(message).catch((err) => {
        console.error('Lỗi gửi yêu cầu phân tích:', err);
      });
    });

    host.appendChild(btn);

    if (postElement.shadowRoot) {
      postElement.shadowRoot.prepend(host);
    } else {
      const titleNode = postElement.querySelector('[slot="title"]');
      if (titleNode) {
        titleNode.prepend(host);
      } else {
        postElement.prepend(host);
      }
    }
  }
}
