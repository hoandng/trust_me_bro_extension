# ROADMAP.md

> Dự án: Extension kiểm chứng độ tin cậy bài đăng mạng xã hội

## Trạng thái hiện tại

- **Giai đoạn:** MVP (demo) có adapter Facebook và Reddit, hỗ trợ chọn model Gemini trong side panel.
- **Cập nhật lần cuối:** 2026-11-10

## Mục tiêu tổng thể

Xây dựng một extension giúp người dùng kiểm tra nhanh độ tin cậy của bất kỳ đoạn nội dung nào trên mạng xã hội, có trích dẫn nguồn rõ ràng, mở rộng dần ra nhiều nền tảng và nhiều nguồn dữ liệu kiểm chứng.

## Milestone 1: MVP Demo trên Facebook

Mục tiêu: chứng minh luồng hoạt động end-to-end.

- [x] Setup project: extension skeleton (Manifest V3) + backend skeleton (FastAPI)
- [x] Content script: bắt sự kiện bôi đen text trên Facebook, hiện nút "Phân tích đoạn văn này"
- [x] Background script: gửi text đã chọn sang backend, nhận response
- [x] Side panel UI: hiển thị kết quả (verdict, độ tin cậy, giải thích, danh sách nguồn)
- [x] Backend: endpoint `POST /api/v1/analyze`
- [x] Service: tích hợp Google Fact Check Tools API
- [x] Service: tích hợp Tavily API (tìm nguồn liên quan)
- [x] Service: tích hợp Gemini API (phân tích + tổng hợp đánh giá cuối)
- [x] Orchestrator: Gemini trích xuất khẳng định, Fact Check và Tavily tra cứu song song, Gemini đánh giá khi có bằng chứng
- [x] Bảo mật cơ bản: API key backend qua `.env`, CORS giới hạn theo extension ID, giới hạn độ dài input
- [x] Test thủ công toàn luồng trên 5-10 bài post Facebook thực tế (có tin thật, tin giả, tin chưa rõ)

## Milestone 2: Ổn định & UX

Mục tiêu: extension dùng được mượt mà, xử lý lỗi tốt, sẵn sàng cho nhóm nhỏ dùng thử.

- [x] Tổ chức extension theo tính năng: entrypoints, features/analysis, infrastructure, shared
- [x] Tách HTTP client, mapper response, trạng thái theo tab, controller và renderer; thêm module tests với mock
- [x] Xử lý trạng thái loading/error rõ ràng trong side panel
- [x] Rate limiting phía backend (tránh spam/tốn quota API trả phí)
- [x] Trả kết quả với trạng thái từng dịch vụ khi nguồn tra cứu lỗi hoặc timeout
- [x] Cho phép chọn model Gemini ưu tiên, lưu lựa chọn và hiển thị model thực tế theo từng bước trong side panel
- [x] Tự chuyển model khi Gemini trả `429`, chia sẻ cooldown trong process và trả `503` kèm `Retry-After` khi hết model khả dụng do quota
- [x] Giới hạn độ dài văn bản được phép gửi phân tích + thông báo rõ cho người dùng
- [x] Ghi metadata của lượt phân tích để debug và theo dõi usage, với giới hạn ghi log được ghi trong [checklist bảo mật](SECURITY_CHECKLIST.md)
- [x] Viết test tự động cho backend (mock 3 API ngoài)
- [x] A1: Chuẩn hóa rating Fact Check tiếng Anh và tiếng Việt, giữ stance gốc và chỉ cho phép nguồn Fact Check đầu tiên đổi verdict khi khớp khẳng định. Có test hồi quy cho `Not true`, stance gốc và điều kiện khớp claim.

## Milestone 3: Nâng cấp tính năng (theo yêu cầu ban đầu)

- [ ] Chèn nút phân tích trực tiếp vào từng bài post ngay trên News Feed của Facebook/Reddit (trang chi tiết bài viết Reddit `/comments/` đã hỗ trợ chèn nút kiểm chứng)
- [ ] Chế độ click vào bài post → tự động phân tích toàn bộ nội dung post đó
- [ ] Cache kết quả phân tích theo hash nội dung: thêm `extension/src/infrastructure/cache/`, TTL và policy của từng tính năng; có thể bổ sung Redis ở backend khi cần cache dùng chung
- [ ] Tóm tắt bài báo: thêm `features/article-summary/`, hợp đồng message và endpoint backend tương ứng
- [ ] Lưu lịch sử phân tích cho người dùng (tuỳ chọn, cần thiết kế lại phần bảo mật/lưu trữ dữ liệu)

## Milestone 4: Mở rộng đa nền tảng

- [ ] Viết adapter cho X (Twitter)
- [x] Viết adapter cho Reddit và chèn nút kiểm chứng trong trang chi tiết bài viết
- [x] Có interface `PlatformAdapter` và registry trong `features/analysis/content/adapters/`
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
