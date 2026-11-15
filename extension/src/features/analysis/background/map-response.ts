import { safeSourceUrl } from '../source-url';
import type { AnalyzeResponse, BackendAnalysisResponse, SourceItem } from '../types';

type VerdictCopy = Pick<AnalyzeResponse, 'verdict' | 'conclusion'>;

const unverified: VerdictCopy = {
  verdict: 'Không thể kiểm chứng',
  conclusion: 'Chưa đủ bằng chứng, đừng vội chia sẻ',
};
const verdicts = new Map<string, VerdictCopy>([
  ['likely_true', { verdict: 'Thật', conclusion: 'Có vẻ đúng sự thật' }],
  ['likely_false', { verdict: 'Giả', conclusion: 'Có vẻ sai sự thật' }],
  ['mixed', { verdict: 'Thiếu ngữ cảnh', conclusion: 'Cần xem thêm ngữ cảnh' }],
  ['unverified', unverified],
]);

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

function mapSource(source: NonNullable<BackendAnalysisResponse['sources']>[number]): SourceItem {
  const url = safeSourceUrl(source.url);
  const stance = source.stance?.trim().toLowerCase();
  return {
    title: source.title,
    url: url?.href ?? '',
    publisher: source.publisher?.trim() || source.publisher_name?.trim() ||
      url?.hostname.replace(/^www\./, '') || 'Nguồn bên ngoài',
    snippet: source.snippet || '',
    stance: stance === 'supports' || stance === 'refutes' || stance === 'neutral' ? stance : undefined,
    publishedDate: formatPublishedDate(source.published_date),
  };
}

export function mapAnalysisResponse(data: BackendAnalysisResponse): AnalyzeResponse {
  const status = data.service_status;
  return {
    request_id: data.request_id,
    model_usage: data.model_usage,
    ...(verdicts.get(data.verdict) ?? unverified),
    confidence: Math.round(data.confidence_score * 100),
    explanation: data.explanation,
    sources: (data.sources || []).map(mapSource),
    service_status:
      status && typeof status === 'object'
        ? Object.values(status).includes('error')
          ? 'error'
          : 'ok'
        : status || 'ok',
  };
}
