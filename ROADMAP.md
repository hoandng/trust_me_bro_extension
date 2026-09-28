# ROADMAP.md

> Dự án: Extension kiểm chứng độ tin cậy bài đăng mạng xã hội

## Trạng thái hiện tại
- **Phiên bản:** v0.1 (demo)
- **Giai đoạn:** MVP — chỉ hỗ trợ Facebook
- **Cập nhật lần cuối:** 2026-09-27

## Mục tiêu tổng thể
Xây dựng một extension giúp người dùng kiểm tra nhanh độ tin cậy của bất kỳ đoạn nội dung nào trên mạng xã hội, có trích dẫn nguồn rõ ràng, mở rộng dần ra nhiều nền tảng và nhiều nguồn dữ liệu kiểm chứng.

## Milestone 1: MVP Demo (Facebook only) — đang làm
Mục tiêu: chứng minh luồng hoạt động end-to-end.

- [ ] Setup project: extension skeleton (Manifest V3) + backend skeleton (FastAPI)
- [ ] Content script: bắt sự kiện bôi đen text trên Facebook, hiện nút "Phân tích đoạn văn này"
- [ ] Background script: gửi text đã chọn sang backend, nhận response
- [ ] Side panel UI: hiển thị kết quả (verdict, độ tin cậy, giải thích, danh sách nguồn)
- [ ] Backend: endpoint `POST /api/v1/analyze`
- [ ] Service: tích hợp Google Fact Check Tools API
- [ ] Service: tích hợp Tavily API (tìm nguồn liên quan)
- [ ] Service: tích hợp Gemini API (phân tích + tổng hợp đánh giá cuối)
- [ ] Orchestrator: gọi song song 3 service, tổng hợp kết quả thành 1 response chuẩn
- [ ] Bảo mật cơ bản: API key backend qua `.env`, CORS giới hạn theo extension ID, giới hạn độ dài input
- [ ] Test thủ công toàn luồng trên 5-10 bài post Facebook thực tế (có tin thật, tin giả, tin chưa rõ)

## Milestone 2: Ổn định & UX
Mục tiêu: extension dùng được mượt mà, xử lý lỗi tốt, sẵn sàng cho nhóm nhỏ dùng thử.

- [ ] Xử lý trạng thái loading/error rõ ràng trong side panel
- [ ] Rate limiting phía backend (tránh spam/tốn quota API trả phí)
- [ ] Retry/fallback khi 1 trong 3 API bên ngoài lỗi hoặc timeout (không để cả response fail vì 1 service hỏng)
- [ ] Giới hạn độ dài văn bản được phép gửi phân tích + thông báo rõ cho người dùng
- [ ] Logging metadata (không log nội dung text đầy đủ) để debug và theo dõi usage
- [ ] Viết test tự động cho backend (mock 3 API ngoài)

## Milestone 3: Nâng cấp tính năng (theo yêu cầu ban đầu)
- [ ] Chèn nút phân tích trực tiếp vào từng bài post (không cần bôi đen thủ công)
- [ ] Chế độ click vào bài post → tự động phân tích toàn bộ nội dung post đó
- [ ] Cache kết quả phân tích (theo hash nội dung) để tránh gọi lại API cho cùng 1 đoạn text — cần thêm database/cache layer (Redis hoặc DB nhẹ)
- [ ] Lưu lịch sử phân tích cho người dùng (tuỳ chọn, cần thiết kế lại phần bảo mật/lưu trữ dữ liệu)

## Milestone 4: Mở rộng đa nền tảng
- [ ] Viết adapter cho X (Twitter)
- [ ] Viết adapter cho Reddit
- [ ] Chuẩn hoá interface adapter để thêm nền tảng mới nhanh hơn
- [ ] Đánh giá thêm API/nguồn dữ liệu kiểm chứng khác (ngoài Fact Check/Gemini/Tavily) để tăng độ chính xác

## Milestone 5: Production-ready
- [ ] Thay static API key bằng cơ chế xác thực chuẩn hơn (issued token/OAuth) giữa extension–backend
- [ ] Giám sát chi phí API (Gemini, Tavily tính phí theo usage) — thêm dashboard/cảnh báo
- [ ] Đăng ký/publish lên Chrome Web Store
- [ ] Chính sách bảo mật & điều khoản sử dụng rõ ràng cho người dùng cuối

## Ghi chú / rủi ro
- Facebook có thể thay đổi cấu trúc DOM bất kỳ lúc nào → content script cần được thiết kế dễ sửa (đã tính trong ARCHITECTURE.md qua adapter pattern)
- Chi phí API (Gemini, Tavily) tăng theo usage thực tế — cần theo dõi khi mở rộng người dùng
- Google Fact Check Tools API có độ phủ dữ liệu tiếng Việt hạn chế — cần đánh giá thêm ở Milestone 2/3, có thể cần bổ sung nguồn khác cho nội dung tiếng Việt
