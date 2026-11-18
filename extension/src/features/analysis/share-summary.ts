import { stripExplanationMarkers } from './explanation-parser';
import { safeSourceUrl } from './source-url';
import type { AnalyzeResponse, SelectionPayload } from './types';

const sentences = new Intl.Segmenter('vi', { granularity: 'sentence' });
const reasonLimit = 160;

function normalize(value: string): string {
  return value.normalize('NFC').trim().replace(/\s+/g, ' ').toLowerCase();
}

function shorten(reason: string): string {
  if (reason.length <= reasonLimit) return reason;
  const prefix = reason.slice(0, reasonLimit - 1);
  const lastSpace = prefix.lastIndexOf(' ');
  return (lastSpace > 0 ? prefix.slice(0, lastSpace) : prefix) + '…';
}

export function buildShareSummary(response: AnalyzeResponse, post?: SelectionPayload): string {
  const privateValues = [post?.text, post?.page_url]
    .filter((value): value is string => !!value)
    .map(normalize)
    .filter(Boolean);
  const containsOriginal = (value: string) => {
    const normalized = normalize(value);
    return privateValues.some((original) => normalized.includes(original));
  };

  const cleanExplanation = stripExplanationMarkers(response.explanation).trim().replace(/\s+/g, ' ');
  const reasons =
    containsOriginal(cleanExplanation) || containsOriginal(response.explanation)
      ? []
      : Array.from(sentences.segment(cleanExplanation), ({ segment }) => segment.trim())
          .filter(Boolean)
          .slice(0, 2)
          .map(shorten);

  const postUrl = post ? safeSourceUrl(post.page_url) : undefined;
  if (postUrl) postUrl.hash = '';
  const links = new Set<string>();
  for (const source of response.sources) {
    const url = safeSourceUrl(source.url);
    if (!url) continue;
    url.hash = '';
    let decodedUrl = url.href;
    try {
      decodedUrl = decodeURIComponent(url.href.replace(/\+/g, ' '));
    } catch {
      // So sánh URL gốc nếu phần mã hóa không hợp lệ.
    }
    if (url.href === postUrl?.href || containsOriginal(url.href) || containsOriginal(decodedUrl)) continue;
    links.add(url.href);
    if (links.size === 2) break;
  }

  const lines = [`Kết luận: ${response.conclusion}`];
  if (reasons.length) lines.push('', ...reasons.map((reason) => `- ${reason}`));
  if (links.size) lines.push('', 'Nguồn tham khảo:', ...links);
  lines.push('', 'Kết quả do AI tổng hợp, chỉ mang tính tham khảo.');
  return lines.join('\n');
}
