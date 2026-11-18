# BUSINESS.md

> Dự án: **Trust Me Bro** – Extension kiểm chứng độ tin cậy nội dung mạng xã hội (Facebook, Reddit)
> Định hướng: **Business-driven**. Mọi quyết định kỹ thuật phải gắn với giá trị cho người dùng và khả năng tạo doanh thu.
>
> Các số liệu đánh dấu **[GIẢ ĐỊNH]** là ước tính ban đầu, cần kiểm chứng bằng khảo sát và thử nghiệm.

## 1. Vấn đề

- Tin giả, tin sai lệch lan nhanh trên Facebook/Reddit, đặc biệt các chủ đề sức khỏe, tài chính, thiên tai.
- Người dùng muốn xác minh nhưng phải rời trang, tự tìm nguồn, mất khoảng 5–10 phút **[GIẢ ĐỊNH]**, nên đa số không kiểm tra.
- Các công cụ fact-check hiện có (Snopes, báo kiểm chứng) chậm, phủ nội dung tiếng Việt hạn chế và không tích hợp ngay tại nơi người dùng đọc tin.
- Hỏi trực tiếp chatbot (ChatGPT, Gemini) thì nhanh nhưng thường không trích dẫn nguồn đáng tin cậy và dễ "bịa".

## 2. Giải pháp và giá trị

Kiểm chứng ngay trên trang đang đọc: bôi đen hoặc bấm nút ở bài viết, trong vài giây nhận được:
- Kết luận (`verdict`) kèm điểm tin cậy.
- Giải thích bằng tiếng Việt.
- Danh sách nguồn có thái độ (Ủng hộ / Bác bỏ / Trung lập).

| Giá trị | Cách đạt được |
|---|---|
| Nhanh | Không rời trang, pipeline chạy song song (Fact Check + Tavily) |
| Đáng tin | Có trích dẫn nguồn, đối chiếu tổ chức fact-check quốc tế |
| Phù hợp tiếng Việt | Giải thích tiếng Việt; bổ sung nguồn báo Việt Nam (xem Roadmap) |
| Rẻ để vận hành | Cache theo hash nội dung, chuyển model khi hết quota |

## 3. Phân khúc khách hàng

| Phân khúc | Nhu cầu | Khả năng trả tiền | Vai trò |
|---|---|---|---|
| **Người dùng cá nhân** (sinh viên, phụ huynh, người lớn tuổi dùng Facebook) | Biết nhanh tin nào đáng tin | Thấp | Beachhead, tạo lượng người dùng |
| **Tòa soạn, nhóm fact-check, truyền thông** | Sàng lọc claim nhanh, tiết kiệm công | Trung bình–cao | Nguồn doanh thu chính |
| **Trường học, tổ chức giáo dục** | Dạy kỹ năng tư duy phản biện, media literacy | Trung bình | Kênh phân phối |
| **Doanh nghiệp, thương hiệu** | Theo dõi tin sai lệch về thương hiệu | Cao | Mở rộng sau |

**Beachhead:** người dùng cá nhân tiếng Việt trên Facebook, kèm pilot với 1–2 nhóm sinh viên hoặc CLB truyền thông.

## 4. Phân tích đối thủ

| Giải pháp | Điểm mạnh | Điểm yếu | Khác biệt của Trust Me Bro |
|---|---|---|---|
| Hỏi ChatGPT/Gemini trực tiếp | Nhanh, tiện | Không có nguồn xác thực, dễ sai | Kết hợp tra cứu thời gian thực + fact-check có trích dẫn |
| Snopes, báo kiểm chứng | Uy tín | Chậm, phủ hẹp, phải tìm thủ công | Tự động, tích hợp ngay trên trang |
| ClaimBuster / Logically / NewsGuard | Có sản phẩm trưởng thành | Thiên về tiếng Anh, giá cao | Tập trung tiếng Việt, giá thấp |
| Community Notes (X/Meta) | Miễn phí, cộng đồng | Chậm, phụ thuộc nền tảng | Phản hồi tức thì theo yêu cầu |

## 5. Mô hình kinh doanh

| Gói | Đối tượng | Nội dung | Giá **[GIẢ ĐỊNH]** |
|---|---|---|---|
| **Free** | Cá nhân | 10 lượt/ngày, model mặc định | 0đ |
| **Pro** | Cá nhân nâng cao | Không giới hạn hợp lý, lịch sử, tóm tắt bài báo | 49.000đ/tháng |
| **Team / Newsroom** | Tòa soạn, trường học | Dashboard, xuất báo cáo, nhiều tài khoản | 499.000đ/tháng/nhóm |
| **API** | Doanh nghiệp, tích hợp | Gọi API theo lượt | Theo usage |

Hiện chạy ở chế độ MVP (rate limit theo IP/key/ngày) nên giới hạn của gói Free đã có sẵn hạ tầng.

## 6. Unit economics (ước tính)

Chi phí cho **một lượt phân tích** gồm:
- Gemini Stage 0 (trích claim) + Stage 2 (tổng hợp).
- 1 lượt Tavily Search.
- 1 lượt Fact Check API (miễn phí theo hạn mức).

| Khoản | Cách tính |
|---|---|
| Chi phí/lượt | `gemini_tokens × đơn giá + tavily_credit` – **đo thực tế từ log `model_usage`** |
| Tỉ lệ cache hit | Mục tiêu ≥ 30% **[GIẢ ĐỊNH]** (giảm chi phí tương ứng) |
| Chi phí/người dùng Free/tháng | `10 lượt × 30 ngày × chi phí/lượt × (1 − cache hit)` |
| Biên lợi nhuận gói Pro | `giá − chi phí biến đổi trung bình/người dùng Pro` |

> **Việc cần làm:** đo chi phí/lượt thực tế trên 50–100 request và điền số vào bảng trên.

## 7. Chỉ số thành công (KPI)

| Nhóm | Chỉ số | Mục tiêu **[GIẢ ĐỊNH]** |
|---|---|---|
| Chất lượng | Accuracy trên bộ dữ liệu claim tiếng Việt có nhãn | ≥ 75% |
| Chất lượng | So với baseline (Gemini thuần / chỉ Fact Check) | Pipeline đầy đủ tốt hơn rõ rệt |
| Trải nghiệm | Thời gian từ bấm đến có kết quả | ≤ 15 giây |
| Tăng trưởng | Người dùng thử nghiệm | 20–50 người |
| Giữ chân | Tỉ lệ dùng lại sau 7 ngày | ≥ 30% |
| Hài lòng | Điểm tin tưởng/hài lòng (khảo sát 1–5) | ≥ 4.0 |
| Chi phí | Chi phí trung bình/lượt | Thấp hơn giá trị doanh thu/lượt |

## 8. Kế hoạch kiểm chứng giả thuyết

| # | Giả thuyết | Cách kiểm chứng | Kết quả cần có |
|---|---|---|---|
| H1 | Người dùng thực sự muốn kiểm chứng ngay trên trang | Khảo sát + thử nghiệm 10–20 người | Tỉ lệ ưu tiên, thời gian tiết kiệm |
| H2 | Pipeline có bằng chứng chính xác hơn Gemini thuần | Benchmark bộ claim có nhãn (thư mục `eval/`) | Bảng so sánh accuracy/chi phí/độ trễ |
| H3 | Người dùng chịu trả cho Pro/Team | Phỏng vấn, landing page đăng ký sớm | Số lượng đăng ký quan tâm |
| H4 | Cache giảm chi phí đáng kể | Đo tỉ lệ cache hit khi pilot | % chi phí giảm |

## 9. Roadmap theo giá trị kinh doanh

Ưu tiên theo tác động lên người dùng và doanh thu, không theo độ khó kỹ thuật.

| Ưu tiên | Hạng mục | Lý do kinh doanh |
|---|---|---|
| P0 | Bộ dữ liệu đánh giá + benchmark so sánh baseline | Chứng minh giá trị, là bằng chứng cho báo cáo |
| P0 | Nút kiểm chứng trên từng bài ở News Feed, click bài để phân tích | Giảm ma sát, tăng số lượt dùng |
| P0 | Cache theo hash nội dung | Giảm chi phí/lượt, tăng tốc độ |
| P1 | Nguồn tiếng Việt (whitelist báo chính thống, fact-check Việt Nam) | Điểm khác biệt, tăng độ chính xác |
| P1 | Đo lường sử dụng và dashboard chi phí | Tính được unit economics thật |
| P1 | Pilot với nhóm sinh viên/CLB, thu feedback | Kiểm chứng H1, H3 |
| P2 | Lịch sử phân tích, tóm tắt bài báo (gói Pro) | Lý do để người dùng trả tiền |
| P2 | Adapter X, OAuth, publish Chrome Web Store | Mở rộng sau khi có tín hiệu thị trường |

## 10. Rủi ro và giảm thiểu

| Rủi ro | Mức độ | Giảm thiểu |
|---|---|---|
| Chi phí Gemini/Tavily tăng theo usage | Cao | Cache, rate limit, đo chi phí/lượt, giới hạn gói Free |
| Kết luận sai gây mất niềm tin | Cao | Hiển thị độ tin cậy + nguồn, disclaimer, đo accuracy định kỳ |
| Facebook đổi DOM | Trung bình | Adapter pattern đã có, test selector |
| Fact Check API ít phủ tiếng Việt | Trung bình | Bổ sung nguồn Việt Nam |
| Quyền riêng tư dữ liệu người dùng | Trung bình | Chỉ gửi đoạn được chọn, chính sách bảo mật (xem [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)) |
| Phụ thuộc nhà cung cấp AI | Trung bình | Orchestrator dễ thay nguồn, đã có chuyển model |

## 11. Liên hệ với tài liệu khác

- Kiến trúc kỹ thuật: [ARCHITECTURE.md](ARCHITECTURE.md)
- Lộ trình kỹ thuật chi tiết: [ROADMAP.md](ROADMAP.md) (cần đồng bộ lại theo mục 9)
- Bảo mật: [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)
