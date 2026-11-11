Ran project structure exploration
Analyzed run_benchmark.py:L1-651
Analyzed dataset.csv:L1-11
Analyzed README.md:L1-39

Tôi đã đọc xong toàn bộ codebase. Đây là sản phẩm **fact-checking / kiểm chứng thông tin** (browser extension + backend AI). Dưới đây là cấu trúc dataset đầy đủ để chạy benchmark:

---

## Cấu trúc Dataset cho Benchmark

### Format bắt buộc — `dataset.csv`

```
id,text,label,topic,source_url,date
```

| Cột          | Kiểu     | Giá trị hợp lệ                                           | Mô tả                         |
| ------------ | -------- | -------------------------------------------------------- | ----------------------------- |
| `id`         | `string` | Duy nhất, không trống                                    | ID định danh mẫu              |
| `text`       | `string` | Không trống                                              | Nội dung claim cần kiểm chứng |
| `label`      | `enum`   | `true` \| `false` \| `mixed` \| `unverified`             | Nhãn ground truth             |
| `topic`      | `enum`   | `health` \| `scam` \| `finance` \| `disaster` \| `other` | Chủ đề                        |
| `source_url` | `string` | URL HTTP(S) hợp lệ                                       | Nguồn tham chiếu cho claim    |
| `date`       | `string` | `YYYY-MM-DD`                                             | Ngày claim xuất hiện          |

---

### Phân phối mẫu khuyến nghị

Để đánh giá chất lượng có ý nghĩa thống kê, bạn cần **đủ mẫu cho mỗi class** vì macro-F1 tính đều 4 nhãn:

```
Tối thiểu: 40 mẫu (10/nhãn)
Khuyến nghị: 100–200 mẫu
```

**Phân phối theo label:**

```
true        ~30%   (thông tin đúng rõ ràng)
false       ~30%   (thông tin sai rõ ràng)
mixed       ~20%   (đúng + sai lẫn lộn)
unverified  ~20%   (không thể xác minh)
```

**Phân phối theo topic:**

```
health      ~25%   (sức khỏe, y tế)
scam        ~25%   (lừa đảo, OTP, thông báo giả)
finance     ~20%   (tài chính, lãi suất)
disaster    ~15%   (thiên tai, bão lũ)
other       ~15%   (khoa học tổng quát, địa lý...)
```

---

### Ví dụ dataset thực tế mở rộng

```csv
id,text,label,topic,source_url,date
h-001,"Vitamin D từ ánh nắng mặt trời giúp cơ thể hấp thu canxi hiệu quả hơn.",true,health,https://www.who.int/news-room/fact-sheets/detail/vitamin-d,2026-10-01
h-002,"Uống nước oxy có thể chữa ung thư và tăng cường miễn dịch gấp 10 lần.",false,health,https://suckhoedoisong.vn/nuoc-oxy,2026-10-02
h-003,"COVID-19 vaccine vừa hiệu quả vừa có thể gây biến chứng hiếm gặp ở một số nhóm.",mixed,health,https://vnexpress.net/vaccine-covid,2026-10-03
h-004,"Thuốc đông y gia truyền bí mật của ông Nguyễn X có thể trị tiểu đường trong 7 ngày.",unverified,health,https://facebook.com/post/xyz,2026-10-04
s-001,"Ngân hàng không bao giờ yêu cầu cung cấp mã OTP qua điện thoại.",true,scam,https://www.sbv.gov.vn/canh-bao-lua-dao,2026-10-05
s-002,"Nhắn tin WINNING để nhận thưởng 500 triệu từ chương trình của Bộ Công an.",false,scam,https://bocongan.gov.vn/canh-bao,2026-10-06
f-001,"Lãi suất gửi tiết kiệm kỳ hạn 12 tháng tại Vietcombank hiện là 4,7%/năm.",true,finance,https://vietcombank.com.vn/lai-suat,2026-10-07
d-001,"Bão số 3 năm 2024 (Yagi) đổ bộ vào miền Bắc Việt Nam gây thiệt hại nghiêm trọng.",true,disaster,https://vnexpress.net/bao-yagi-2024,2026-10-08
o-001,"Trái Đất quay quanh Mặt Trời với chu kỳ xấp xỉ 365,25 ngày.",true,other,https://nasa.gov/solar-system/earth,2026-10-09
```

---

### Hướng dẫn tạo các loại mẫu khó

| Loại mẫu                   | Mô tả                                                  | Lý do quan trọng                            |
| -------------------------- | ------------------------------------------------------ | ------------------------------------------- |
| **Factual hard negatives** | Sai một chi tiết nhỏ ("3 loại" thay vì "4 loại")       | Test độ nhạy của model                      |
| **Mixed claims**           | Câu có 2 vế, một đúng một sai                          | Test khả năng phân tách                     |
| **Unverifiable events**    | Sự kiện cục bộ, không có nguồn online                  | Test khi Fact Check + Tavily không tìm được |
| **Scam patterns**          | Template lừa đảo OTP, giải thưởng, trúng số            | Domain quan trọng nhất của sản phẩm         |
| **Contradictory sources**  | Claim mà các nguồn khác nhau đưa ra verdict ngược nhau | Test xử lý `mixed`                          |

---

### Checklist trước khi chạy benchmark

```bash
# Kiểm tra format dataset
python scripts/benchmark/run_benchmark.py --dataset path/to/dataset.csv --cache-only

# Chạy thử 5 mẫu đầu
python scripts/benchmark/run_benchmark.py --dataset path/to/dataset.csv --limit 5

# Chạy toàn bộ
python scripts/benchmark/run_benchmark.py --dataset path/to/dataset.csv
```

> [!IMPORTANT]
> Dataset hiện tại ([`dataset.csv`](file:///f:/UTC/Nam_5/Enterprise_Application/trust-me-bro/scripts/benchmark/dataset.csv)) chỉ có 10 mẫu minh họa với `source_url` giả (`example.invalid`). Bạn cần tạo file CSV riêng với URL thật để chạy benchmark thực sự — `source_url` chỉ dùng để tham chiếu và chấm điểm nguồn, không ảnh hưởng logic phân loại.

> [!TIP]
> Sau khi chạy, benchmark sinh ra file `benchmark_<ngày>_citations.csv`. Bạn điền cột `supports_verdict` = `true`/`false` để đánh giá **citation validity** — tỷ lệ nguồn mà hệ thống trích dẫn thực sự củng cố verdict của nó.
