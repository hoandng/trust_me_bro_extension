export interface AnalyzeRequest {
  postId: string;
  content: string;
}

export interface AnalyzeResponse {
  isFake: boolean;
  confidence: number;
  explanation: string;
}

export type ExtensionMessage =
  | { type: 'ANALYZE_POST'; payload: AnalyzeRequest }
  | { type: 'ANALYZE_RESULT'; payload: AnalyzeResponse };
