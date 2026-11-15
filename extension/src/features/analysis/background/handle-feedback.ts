import { postToBackend } from '../../../infrastructure/api/backend-client';
import type { SubmitFeedbackMessage } from '../../../shared/messages';
import type { FeedbackReply, FeedbackSubmission, TabAnalysisState } from '../types';
import { getLiveAnalysisState } from './handle-analysis';

const pendingFeedback = new WeakSet<TabAnalysisState>();

export async function handleFeedback(message: SubmitFeedbackMessage): Promise<FeedbackReply> {
  const { tabId, request_id, helpful } = message;
  const state = getLiveAnalysisState(tabId);
  if (state?.status !== 'success' || state.response?.request_id !== request_id) {
    return { ok: false, error: 'Kết quả này đã thay đổi. Hãy phản hồi trên kết quả hiện tại.' };
  }
  if (pendingFeedback.has(state)) {
    return { ok: false, error: 'Đang gửi phản hồi cho kết quả này.' };
  }
  if (state.feedback === helpful) return { ok: true };

  pendingFeedback.add(state);
  try {
    const body: FeedbackSubmission = { request_id, helpful };
    await postToBackend<void>('/api/v1/feedback', body);
    state.feedback = helpful;
    return { ok: true };
  } catch {
    return { ok: false, error: 'Chưa gửi được phản hồi. Hãy thử lại sau.' };
  } finally {
    pendingFeedback.delete(state);
  }
}
