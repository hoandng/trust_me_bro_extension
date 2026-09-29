import { AnalyzeResponse } from './types';

export const getMockResponse = (): Promise<AnalyzeResponse> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        verdict: 'Giả',
        confidence: 95,
        explanation: 'Thông tin này không có cơ sở khoa học và đã bị nhiều tổ chức y tế uy tín bác bỏ.',
        sources: [
          { title: 'Tổ chức Y tế Thế giới (WHO)', url: 'https://who.int' },
          { title: 'Bộ Y tế Việt Nam', url: 'https://moh.gov.vn' }
        ]
      });
    }, 1500);
  });
};
