# BUSINESS

Tài liệu định hướng kinh doanh, phân khúc khách hàng, giả định mô hình doanh thu và KPI của TrustMeBro. Các số liệu gắn nhãn **[GIẢ ĐỊNH]** chưa được kiểm chứng thực nghiệm.

Cập nhật: 19/11/2026.

## 1. Vấn đề

- Tin sai lệch lan truyền trên Facebook và Reddit ở các chủ đề sức khỏe, tài chính, lừa đảo và thiên tai.
- Người dùng muốn đối chiếu thông tin phải rời trang đang đọc để tự tìm nguồn (ước tính 5–10 phút **[GIẢ ĐỊNH]**).
- Các trang fact-check độc lập có độ phủ tiếng Việt hạn chế và tách rời ngữ cảnh đọc tin.
- Hỏi trực tiếp chatbot không kèm tìm kiếm dễ thiếu nguồn trích dẫn và tạo thông tin không có căn cứ.

## 2. Giải pháp và giá trị

Kiểm chứng văn bản ngay tại trang đang đọc trên Facebook và Reddit qua Side Panel:

- Kết luận 4 mức (`likely_true`, `likely_false`, `mixed`, `unverified`) và mức chắc chắn 3 vạch (`Thấp`, `Vừa`, `Cao`).
- Giải thích ngắn bằng tiếng Việt kèm đánh dấu inline (`✓`, `✗`, `?`).
- Danh sách tối đa 8 nguồn kèm thái độ (`Ủng hộ`, `Phản bác`, `Liên quan`) và tên nhà xuất bản.

| Giá trị            | Cơ chế kỹ thuật hiện có                                                                                                |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| Kiểm chứng tại chỗ | Extension bôi đen 20–2000 ký tự trên Facebook/Reddit, nút kiểm chứng bài viết trên `/comments/` Reddit                 |
| Đối chiếu nguồn    | Tra cứu song song Google Fact Check Tools API và Tavily Search API, xếp hạng theo 32 tên miền (`trusted_domains.json`) |
| Hỗ trợ tiếng Việt  | Giải thích tiếng Việt, chuẩn hóa nhãn Fact Check EN/VI, 28 tên miền cơ quan/báo chí Việt Nam                           |
| Kiểm soát chi phí  | Cache SQLite theo hash/prompt/model/lang, rate limit 3 tầng và xoay vòng model khi HTTP `429`                          |

Chi tiết kỹ thuật xem [ARCHITECTURE.md](ARCHITECTURE.md) và [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md).

## 3. Phân khúc khách hàng

| Phân khúc                                          | Nhu cầu                                     | Khả năng trả tiền **[GIẢ ĐỊNH]** | Vai trò                      |
| -------------------------------------------------- | ------------------------------------------- | -------------------------------- | ---------------------------- |
| Người dùng cá nhân (đọc tin trên Facebook, Reddit) | Kiểm chứng claim trước khi tin hoặc chia sẻ | Thấp                             | Tạo lượng người dùng ban đầu |
| Tòa soạn, nhóm fact-check, truyền thông            | Sàng lọc claim có dẫn nguồn                 | Trung bình–cao                   | Nguồn doanh thu chính        |
| Trường học, tổ chức giáo dục                       | Hỗ trợ giảng dạy kỹ năng đọc hiểu tin tức   | Trung bình                       | Kênh phân phối               |
| Doanh nghiệp, thương hiệu                          | Theo dõi tin sai lệch liên quan thương hiệu | Cao                              | Mở rộng về sau               |

## 4. So sánh phương án thay thế

| Giải pháp                  | Điểm mạnh                      | Giới hạn                                       | Cách tiếp cận của TrustMeBro                           |
| -------------------------- | ------------------------------ | ---------------------------------------------- | ------------------------------------------------------ |
| Chatbot AI thuần           | Phản hồi trực tiếp             | Không bắt buộc đối chiếu nguồn ngoài           | Kết hợp tra cứu Fact Check + Tavily trước khi đánh giá |
| Trang fact-check thủ công  | Quy trình biên tập độc lập     | Rời khỏi trang đang đọc, độ phủ tiếng Việt hẹp | Tích hợp trực tiếp trên trang mạng xã hội              |
| Công cụ kiểm chứng quốc tế | Sản phẩm thương mại hoàn thiện | Thiên về tiếng Anh, chi phí cao                | Hỗ trợ giao diện và nguồn báo chí tiếng Việt           |
| Community Notes            | Dựa vào cộng đồng              | Phụ thuộc nền tảng và độ trễ đóng góp          | Phản hồi theo yêu cầu của người đọc                    |

## 5. Mô hình doanh thu dự kiến **[GIẢ ĐỊNH]**

| Gói             | Đối tượng            | Phạm vi dự kiến                                 | Giá **[GIẢ ĐỊNH]**  |
| --------------- | -------------------- | ----------------------------------------------- | ------------------- |
| Free            | Cá nhân              | 10 lượt/ngày, model mặc định                    | 0đ                  |
| Pro             | Cá nhân nâng cao     | Hạn mức cao, lịch sử phân tích, tóm tắt bài báo | 49.000đ/tháng       |
| Team / Newsroom | Tòa soạn, trường học | Dashboard, xuất báo cáo, nhiều tài khoản        | 499.000đ/tháng/nhóm |
| API             | Doanh nghiệp         | Tính phí theo lượt gọi                          | Theo usage          |

Hiện mã nguồn chạy chế độ MVP với khóa tĩnh dùng chung (`RATE_LIMIT_PER_DAY_KEY=100` trên toàn bộ key), chưa có xác thực theo tài khoản để phân gói Free/Pro.

## 6. Kinh tế đơn vị (Unit economics)

Chi phí cho mỗi lượt miss cache gồm:

- 2 lời gọi Gemini Interactions API (Stage 0 trích xuất và Stage 2 đánh giá; dừng sớm sau Stage 0 nếu `is_checkable=false` hoặc rỗng nguồn).
- Tối đa 4 lời gọi Tavily Search API (`SEARCH_QUERY_LIMIT` tối đa 2 truy vấn × tối đa 2 topic `news` → `general`).
- Tối đa 4 lời gọi Google Fact Check Tools API (tối đa 2 truy vấn × tối đa 2 lần gọi có/không `languageCode`).

Backend tính `estimated_cost_usd` cho từng lượt trong `backend/data/metrics.db` (`analysis_metrics`) và tổng hợp `cost_per_check_usd` tại `GET /api/v1/stats/summary` khi cấu hình `GEMINI_TOKEN_PRICES` và `TAVILY_USD_PER_CREDIT`. Tỷ lệ cache hit mục tiêu: `>= 30%` **[GIẢ ĐỊNH]**.

## 7. Chỉ số thành công (KPI) **[GIẢ ĐỊNH]**

| Nhóm        | Chỉ số                                           | Mục tiêu **[GIẢ ĐỊNH]**                                  |
| ----------- | ------------------------------------------------ | -------------------------------------------------------- |
| Chất lượng  | Accuracy trên bộ claim tiếng Việt có nhãn        | `>= 75%`                                                 |
| Chất lượng  | Chênh lệch Macro-F1 của `full` so với `llm_only` | `>= +0.10`, `p < 0.05` (ngưỡng trong `run_benchmark.py`) |
| Trải nghiệm | Độ trễ p95                                       | `<= 15` giây                                             |
| Tăng trưởng | Số người dùng thử nghiệm                         | 20–50 người                                              |
| Giữ chân    | Tỷ lệ quay lại sau 7 ngày                        | `>= 30%`                                                 |
| Hài lòng    | Điểm đánh giá khảo sát (thang 1–5)               | `>= 4.0`                                                 |

## 8. Kế hoạch kiểm chứng giả thuyết

| Mã  | Giả thuyết                                       | Cách kiểm chứng                                                  |
| --- | ------------------------------------------------ | ---------------------------------------------------------------- |
| H1  | Người dùng có nhu cầu kiểm chứng ngay trên trang | Khảo sát và thử nghiệm 10–20 người                               |
| H2  | Pipeline có bằng chứng đạt F1 cao hơn `llm_only` | Chạy benchmark 3 chế độ tại `scripts/benchmark/run_benchmark.py` |
| H3  | Người dùng chấp nhận trả phí cho gói Pro/Team    | Phỏng vấn và trang đăng ký thử nghiệm                            |
| H4  | Cache giảm chi phí API theo tỷ lệ cache hit      | Theo dõi `cache_hit` và `cost_per_check_usd` trong `metrics.db`  |

## 9. Ưu tiên theo giá trị kinh doanh

Trạng thái thực thi kỹ thuật được quản lý tại [ROADMAP.md](ROADMAP.md).

| Ưu tiên | Hạng mục                                                               | Trạng thái kỹ thuật                    |
| ------- | ---------------------------------------------------------------------- | -------------------------------------- |
| P0      | Bộ dữ liệu và benchmark 3 chế độ (`scripts/benchmark/`)                | Đã làm                                 |
| P0      | Cache kết quả phân tích trong SQLite (`analysis_cache.py`)             | Đã làm                                 |
| P0      | Nút kiểm chứng trên News Feed Facebook và Reddit                       | Dự kiến (mới có ở `/comments/` Reddit) |
| P1      | Nguồn tin cậy Việt Nam trong `trusted_domains.json`                    | Đã làm (28 tên miền Việt Nam)          |
| P1      | Đo lường sử dụng và chi phí (`metrics.db`, `/api/v1/stats/summary`)    | Đã làm (chưa có dashboard UI)          |
| P1      | Đánh giá 5 sao kèm nhận xét (`POST /api/v1/feedback`)                 | Đã làm                                 |
| P1      | Thử nghiệm pilot với nhóm người dùng                                   | Dự kiến                                |
| P2      | Lịch sử phân tích, tóm tắt bài báo, adapter X, OAuth, Chrome Web Store | Dự kiến                                |

## 10. Rủi ro kinh doanh và giảm thiểu

| Rủi ro                                    | Mức độ     | Biện pháp                                                                                                                 |
| ----------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------- |
| Chi phí Gemini/Tavily tăng theo lưu lượng | Cao        | Áp dụng cache SQLite, rate limit 3 tầng và theo dõi `estimated_cost_usd`                                                  |
| Kết luận sai làm giảm độ tin cậy          | Cao        | Hiển thị mức chắc chắn 3 vạch, trích dẫn nguồn, cảnh báo AI và đo benchmark định kỳ                                       |
| Facebook/Reddit thay đổi DOM              | Trung bình | Tách logic DOM vào `PlatformAdapter`, ưu tiên `window.getSelection()`                                                     |
| Fact Check API ít phủ tiếng Việt          | Trung bình | Kết hợp Tavily Search và xếp hạng 28 tên miền Việt Nam                                                                    |
| Quyền riêng tư dữ liệu người dùng         | Trung bình | Không lưu bài đăng gốc trong `metrics.db`, log hoặc `chrome.storage` (xem [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)) |
| Phụ thuộc nhà cung cấp AI                 | Trung bình | Tách lớp `services/` và xoay vòng nhiều model qua `GeminiModelPool`                                                       |
