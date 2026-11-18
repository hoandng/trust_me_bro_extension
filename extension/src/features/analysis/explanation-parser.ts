export type ExplanationSegmentStatus = 'plain' | 'confirmed' | 'refuted' | 'unverified';

export interface ExplanationSegment {
  text: string;
  status: ExplanationSegmentStatus;
}

export const MAX_EXPLANATION_MARKERS = 4;

const prefixToStatus: Record<string, ExplanationSegmentStatus | undefined> = {
  '+': 'confirmed',
  '-': 'refuted',
  '?': 'unverified',
};

const statusSymbols: Record<Exclude<ExplanationSegmentStatus, 'plain'>, string> = {
  confirmed: '✓',
  refuted: '✗',
  unverified: '?',
};

/**
 * Loại bỏ toàn bộ ký hiệu đánh dấu [[+...]], [[-...]], [[?...]] để lấy văn bản thuần.
 */
export function stripExplanationMarkers(input: string): string {
  if (!input) return '';
  let result = input
    .split('[[+')
    .join('')
    .split('[[-')
    .join('')
    .split('[[?')
    .join('');
  while (result.includes('[[') || result.includes(']]')) {
    result = result.split('[[').join('').split(']]').join('');
  }
  return result;
}

function fallbackPlain(input: string): ExplanationSegment[] {
  const cleaned = stripExplanationMarkers(input);
  return cleaned ? [{ text: cleaned, status: 'plain' }] : [];
}

/**
 * Parser thuần (không regex nặng, không innerHTML) tách chuỗi explanation
 * thành các đoạn { text, status }. Nếu sai cú pháp, không cân bằng, lồng nhau
 * hoặc vượt quá 4 đoạn đánh dấu thì trả về một đoạn plain text đã bỏ ký hiệu.
 */
export function parseExplanation(input: string): ExplanationSegment[] {
  if (!input) return [];
  if (!input.includes('[[') && !input.includes(']]')) {
    return [{ text: input, status: 'plain' }];
  }

  const segments: ExplanationSegment[] = [];
  let cursor = 0;
  let markerCount = 0;

  while (cursor < input.length) {
    const openIdx = input.indexOf('[[', cursor);
    const strayCloseIdx = input.indexOf(']]', cursor);

    if (strayCloseIdx !== -1 && (openIdx === -1 || strayCloseIdx < openIdx)) {
      return fallbackPlain(input);
    }

    if (openIdx === -1) {
      if (cursor < input.length) {
        segments.push({ text: input.slice(cursor), status: 'plain' });
      }
      break;
    }

    if (openIdx > cursor) {
      segments.push({ text: input.slice(cursor, openIdx), status: 'plain' });
    }

    const prefix = input[openIdx + 2];
    const status = prefix ? prefixToStatus[prefix] : undefined;
    if (!status) {
      return fallbackPlain(input);
    }

    markerCount += 1;
    if (markerCount > MAX_EXPLANATION_MARKERS) {
      return fallbackPlain(input);
    }

    const contentStart = openIdx + 3;
    const closeIdx = input.indexOf(']]', contentStart);
    if (closeIdx === -1) {
      return fallbackPlain(input);
    }

    const content = input.slice(contentStart, closeIdx);
    if (!content.trim() || content.includes('[[') || content.includes(']]')) {
      return fallbackPlain(input);
    }

    segments.push({ text: content, status });
    cursor = closeIdx + 2;
  }

  return segments;
}

/**
 * Dựng nội dung giải thích vào phần tử DOM chỉ bằng createElement và textContent.
 */
export function renderExplanationSegments(
  container: HTMLElement,
  explanation: string,
  doc: Document = document,
): void {
  container.replaceChildren();
  const segments = parseExplanation(explanation);
  for (const segment of segments) {
    if (segment.status === 'plain') {
      const span = doc.createElement('span');
      span.textContent = segment.text;
      container.appendChild(span);
    } else {
      const mark = doc.createElement('span');
      mark.className = `explanation-mark mark-${segment.status}`;

      const icon = doc.createElement('span');
      icon.className = 'mark-symbol';
      icon.setAttribute('aria-hidden', 'true');
      icon.textContent = `${statusSymbols[segment.status]} `;

      const textNode = doc.createElement('span');
      textNode.className = 'mark-text';
      textNode.textContent = segment.text;

      mark.appendChild(icon);
      mark.appendChild(textNode);
      container.appendChild(mark);
    }
  }
}
