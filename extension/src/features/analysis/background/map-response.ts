import publisherNames from '../publisher-names.json';
import { safeSourceUrl } from '../source-url';
import type {
  AnalyzeResponse,
  BackendAnalysisResponse,
  ConfidenceBars,
  ConfidenceLevel,
  SourceItem,
  SourceStance,
  SourceStanceLabel,
} from '../types';

type VerdictCopy = Pick<AnalyzeResponse, 'verdict_key' | 'verdict' | 'conclusion' | 'subtext'>;

const unverified: VerdictCopy = {
  verdict_key: 'unverified',
  verdict: 'Không thể kiểm chứng',
  conclusion: 'Chưa đủ bằng chứng',
  subtext: 'Đừng vội chia sẻ tin này.',
};

const verdicts = new Map<string, VerdictCopy>([
  ['likely_true', { verdict_key: 'likely_true', verdict: 'Thật', conclusion: 'Có vẻ đúng' }],
  ['likely_false', { verdict_key: 'likely_false', verdict: 'Giả', conclusion: 'Có vẻ sai sự thật' }],
  ['mixed', { verdict_key: 'mixed', verdict: 'Thiếu ngữ cảnh', conclusion: 'Đúng một phần' }],
  ['unverified', unverified],
]);

const stanceLabelMap: Record<SourceStance, SourceStanceLabel> = {
  supports: 'Ủng hộ',
  refutes: 'Phản bác',
  neutral: 'Liên quan',
};

const normalizedPublisherMap = new Map<string, string>(
  Object.entries(publisherNames).map(([domain, name]) => [
    domain.toLowerCase().replace(/\.$/, ''),
    name,
  ]),
);

const sentenceSegmenter = new Intl.Segmenter('vi', { granularity: 'sentence' });
const DEFAULT_SNIPPET_MAX_LENGTH = 140;

const sourceDateFormatter = new Intl.DateTimeFormat('vi-VN', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  timeZone: 'Asia/Ho_Chi_Minh',
});

function formatPublishedDate(value?: string | null): string | undefined {
  const raw = value?.trim();
  if (!raw) return undefined;
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return undefined;
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw) && date.toISOString().slice(0, 10) !== raw) {
    return undefined;
  }
  return sourceDateFormatter.format(date);
}

export function lookupPublisherByHostname(hostname: string): string | undefined {
  const cleanHost = hostname.toLowerCase().replace(/\.$/, '').replace(/^www\./, '');
  if (!cleanHost) return undefined;

  let bestDomain = '';
  let bestName: string | undefined;
  for (const [domain, name] of normalizedPublisherMap.entries()) {
    if (cleanHost === domain || cleanHost.endsWith(`.${domain}`)) {
      if (domain.length > bestDomain.length) {
        bestDomain = domain;
        bestName = name;
      }
    }
  }
  return bestName;
}

export function resolvePublisherName(
  urlObj: URL | undefined,
  publisher?: string | null,
  publisherName?: string | null,
): string {
  const host = urlObj?.hostname.toLowerCase().replace(/\.$/, '').replace(/^www\./, '') ?? '';
  if (host) {
    const mappedByUrl = lookupPublisherByHostname(host);
    if (mappedByUrl) return mappedByUrl;
  }

  for (const candidate of [publisher, publisherName]) {
    const trimmed = candidate?.trim();
    if (!trimmed) continue;
    const mappedCandidate = lookupPublisherByHostname(trimmed);
    if (mappedCandidate) return mappedCandidate;
    // Nếu backend đã cung cấp tên hiển thị khác với domain thô thì giữ tên đó.
    const cleanCandidate = trimmed.toLowerCase().replace(/\.$/, '').replace(/^www\./, '');
    if (cleanCandidate !== host) {
      return trimmed;
    }
  }

  return host || 'Nguồn bên ngoài';
}

export function truncateSnippet(
  snippet?: string | null,
  maxLength: number = DEFAULT_SNIPPET_MAX_LENGTH,
): string {
  const cleaned = (snippet ?? '').trim().replace(/\s+/g, ' ');
  if (!cleaned || cleaned.length <= maxLength) return cleaned;

  let accumulated = '';
  for (const { segment } of sentenceSegmenter.segment(cleaned)) {
    const candidate = accumulated + segment;
    if (candidate.trim().length > maxLength) break;
    accumulated = candidate;
  }

  const trimmedSentences = accumulated.trim();
  if (trimmedSentences && /[.!?…]["'”’)]*$/.test(trimmedSentences)) {
    return trimmedSentences;
  }

  const prefix = cleaned.slice(0, Math.max(1, maxLength - 1));
  const lastSpace = prefix.lastIndexOf(' ');
  const cut = lastSpace > 0 ? prefix.slice(0, lastSpace) : prefix;
  return `${cut.replace(/[.,;:!?-]+$/, '')}…`;
}

export function mapConfidenceLevel(score: number): {
  confidence_level: ConfidenceLevel;
  confidence_bars: ConfidenceBars;
} {
  if (!Number.isFinite(score) || score < 0.5) {
    return { confidence_level: 'Thấp', confidence_bars: 1 };
  }
  if (score < 0.75) {
    return { confidence_level: 'Vừa', confidence_bars: 2 };
  }
  return { confidence_level: 'Cao', confidence_bars: 3 };
}

function mapSource(source: NonNullable<BackendAnalysisResponse['sources']>[number]): SourceItem {
  const url = safeSourceUrl(source.url);
  const rawStance = source.stance?.trim().toLowerCase();
  const stance: SourceStance =
    rawStance === 'supports' || rawStance === 'refutes' || rawStance === 'neutral'
      ? rawStance
      : 'neutral';

  return {
    title: source.title,
    url: url?.href ?? '',
    publisher: resolvePublisherName(url, source.publisher, source.publisher_name),
    snippet: truncateSnippet(source.snippet),
    stance,
    stanceLabel: stanceLabelMap[stance],
    publishedDate: formatPublishedDate(source.published_date),
  };
}

export function mapAnalysisResponse(data: BackendAnalysisResponse): AnalyzeResponse {
  const status = data.service_status;
  const sources = (data.sources || []).map(mapSource);
  const allSourcesNeutral = sources.length > 0 && sources.every((s) => s.stance === 'neutral');

  return {
    request_id: data.request_id,
    model_usage: data.model_usage,
    ...(verdicts.get(data.verdict) ?? unverified),
    ...mapConfidenceLevel(data.confidence_score),
    explanation: data.explanation,
    sources,
    all_sources_neutral: allSourcesNeutral,
    service_status:
      status && typeof status === 'object'
        ? Object.values(status).includes('error')
          ? 'error'
          : 'ok'
        : status || 'ok',
  };
}
