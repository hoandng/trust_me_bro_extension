import { postToBackend } from '../../../infrastructure/api/backend-client';
import type { SelectionPayload, AnalyzeResponse, BackendAnalysisResponse } from '../types';
import { mapAnalysisResponse } from './map-response';

export async function analyzeSelection(payload: SelectionPayload): Promise<AnalyzeResponse> {
  const response = await postToBackend<BackendAnalysisResponse>('/api/v1/analyze', payload);
  return mapAnalysisResponse(response);
}
