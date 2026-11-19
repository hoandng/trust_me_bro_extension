// Vite và background dùng cùng đường dẫn để manifest và side panel luôn khớp nhau.
export const SIDEPANEL_PATH = 'src/entrypoints/sidepanel/index.html';

// Cờ bật/tắt gửi đánh giá 5 sao lên backend.
export const FEEDBACK_ENDPOINT_ENABLED = true;

let feedbackEndpointEnabled = FEEDBACK_ENDPOINT_ENABLED;

export function isFeedbackEndpointEnabled(): boolean {
  return feedbackEndpointEnabled;
}

export function setFeedbackEndpointEnabled(enabled: boolean): void {
  feedbackEndpointEnabled = enabled;
}
