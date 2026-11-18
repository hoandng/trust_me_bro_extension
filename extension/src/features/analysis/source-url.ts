export function safeSourceUrl(value: string): URL | undefined {
  try {
    const url = new URL(value);
    if ((url.protocol === 'https:' || url.protocol === 'http:') && !url.username && !url.password) {
      return url;
    }
  } catch {
    // Nguồn thiếu URL hợp lệ vẫn có thể hiển thị dưới dạng văn bản.
  }
}
