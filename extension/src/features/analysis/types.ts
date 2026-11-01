export interface SelectionPayload {
  text: string;
  platform: string;
  page_url: string;
}

export interface SourceItem {
  title: string;
  url: string;
  publisher?: string;
  snippet?: string;
  stance?: string;
}

export interface AnalyzeResponse {
  verdict: 'Thật' | 'Giả' | 'Thiếu ngữ cảnh' | 'Không thể kiểm chứng';
  confidence: number;
  explanation: string;
  sources: SourceItem[];
  service_status?: string;
}

export type AnalysisStatus = 'idle' | 'loading' | 'success' | 'error';

export interface TabAnalysisState {
  status: AnalysisStatus;
  request?: SelectionPayload;
  response?: AnalyzeResponse;
  error?: string;
}

export interface BackendAnalysisResponse {
  verdict: string;
  confidence_score: number;
  explanation: string;
  sources?: Array<{
    title: string;
    url: string;
    publisher_name?: string;
    publisher?: string;
    snippet?: string;
    stance?: string;
  }>;
  service_status?: Record<string, string> | string;
}
