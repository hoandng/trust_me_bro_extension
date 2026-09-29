export interface AnalyzeRequest {
  postId: string;
  content: string;
}

export interface AnalyzeResponse {
  verdict: 'Thật' | 'Giả' | 'Thiếu ngữ cảnh' | 'Không thể kiểm chứng';
  confidence: number;
  explanation: string;
  sources: Array<{ title: string; url: string }>;
}

export type AnalysisStatus = 'idle' | 'loading' | 'success' | 'error';

export interface TabAnalysisState {
  status: AnalysisStatus;
  request?: SelectionPayload;
  response?: AnalyzeResponse;
  error?: string;
}

export interface SelectionPayload {
  text: string;
  platform: string;
  page_url: string;
}

export type ExtensionMessage =
  | { type: 'ANALYZE_POST'; payload: AnalyzeRequest }
  | { type: 'ANALYZE_RESULT'; payload: AnalyzeResponse }
  | { type: 'ANALYZE_REQUEST'; payload: SelectionPayload; tabId?: number };
