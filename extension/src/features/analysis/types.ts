export interface SelectionPayload {
  text: string;
  platform: string;
  page_url: string;
  model_id?: string;
}

export type VerdictKey = 'likely_true' | 'likely_false' | 'mixed' | 'unverified';
export type ConfidenceLevel = 'Thấp' | 'Vừa' | 'Cao';
export type ConfidenceBars = 1 | 2 | 3;
export type SourceStance = 'supports' | 'refutes' | 'neutral';
export type SourceStanceLabel = 'Ủng hộ' | 'Phản bác' | 'Liên quan';

export interface SourceItem {
  title: string;
  url: string;
  publisher?: string;
  snippet?: string;
  stance: SourceStance;
  stanceLabel: SourceStanceLabel;
  publishedDate?: string;
}

export interface ModelUsage {
  requested_model: string;
  extraction_model: string | null;
  assessment_model: string | null;
  fallbacks: Array<{ stage: string; model: string; reason: string }>;
}

export interface AnalyzeResponse {
  request_id?: string;
  model_usage?: ModelUsage | null;
  verdict_key: VerdictKey;
  verdict: 'Thật' | 'Giả' | 'Thiếu ngữ cảnh' | 'Không thể kiểm chứng';
  conclusion: 'Có vẻ đúng' | 'Có vẻ sai sự thật' | 'Đúng một phần' | 'Chưa đủ bằng chứng';
  subtext?: string;
  confidence_level: ConfidenceLevel;
  confidence_bars: ConfidenceBars;
  explanation: string;
  sources: SourceItem[];
  all_sources_neutral: boolean;
  service_status?: string;
  duration_ms?: number;
}

export type AnalysisStatus = 'idle' | 'loading' | 'success' | 'error';

export interface StoredTabAnalysisState {
  status: AnalysisStatus;
  request_id?: string;
}

export type FeedbackRating = 1 | 2 | 3 | 4 | 5;

export interface FeedbackSubmission {
  request_id: string;
  rating: FeedbackRating;
  comment?: string;
}

export interface TabAnalysisState {
  status: AnalysisStatus;
  request?: SelectionPayload;
  response?: AnalyzeResponse;
  error?: string;
  feedback?: FeedbackSubmission;
}

export type FeedbackReply = { ok: true } | { ok: false; error: string };

export interface BackendAnalysisResponse {
  request_id?: string;
  model_usage?: ModelUsage | null;
  verdict: string;
  confidence_score: number;
  explanation: string;
  sources?: Array<{
    title: string;
    url: string;
    publisher_name?: string | null;
    publisher?: string | null;
    snippet?: string | null;
    stance?: string | null;
    published_date?: string | null;
  }>;
  service_status?: Record<string, string> | string;
}
