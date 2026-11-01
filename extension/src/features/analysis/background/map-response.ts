import type { AnalyzeResponse, BackendAnalysisResponse } from '../types';

const verdicts: Record<string, AnalyzeResponse['verdict']> = {
  likely_true: 'Thật',
  likely_false: 'Giả',
  mixed: 'Thiếu ngữ cảnh',
  unverified: 'Không thể kiểm chứng',
};

export function mapAnalysisResponse(data: BackendAnalysisResponse): AnalyzeResponse {
  const status = data.service_status;
  return {
    verdict: verdicts[data.verdict] || 'Không thể kiểm chứng',
    confidence: Math.round(data.confidence_score * 100),
    explanation: data.explanation,
    sources: (data.sources || []).map((source) => ({
      title: source.title,
      url: source.url,
      publisher: source.publisher_name || source.publisher || '',
      snippet: source.snippet || '',
      stance: source.stance || '',
    })),
    service_status:
      status && typeof status === 'object'
        ? Object.values(status).includes('error')
          ? 'error'
          : 'ok'
        : status || 'ok',
  };
}
