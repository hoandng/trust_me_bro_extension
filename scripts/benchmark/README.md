# Benchmark kiểm chứng

`dataset.csv` có 10 mẫu minh họa để thử định dạng và chạy test. Dùng một CSV riêng cho dataset thật. Header phải là `id,text,label,topic,source_url,date`. Dùng ID duy nhất, URL HTTP(S) và ngày theo `YYYY-MM-DD`. Các nhãn hợp lệ là `true`, `false`, `mixed`, `unverified`. Các topic là `health`, `scam`, `finance`, `disaster`, `other`. Runner đưa văn bản vào hệ thống kiểm chứng và giữ nhãn, topic, ngày và URL tham chiếu cho việc tổ chức hoặc chấm dataset.

Chạy từ thư mục gốc bằng môi trường Python của backend. Khi chạy với provider thật, cấu hình các API key trong `backend/.env`.

```bash
python scripts/benchmark/run_benchmark.py --dataset path/to/your-dataset.csv --limit 10
```

| Chế độ | Luồng xử lý |
|---|---|
| `llm_only` | Gemini dùng kiến thức sẵn có để phân loại. |
| `factcheck_only` | Google Fact Check tra theo văn bản. Chỉ dùng review có claim trùng sau chuẩn hóa Unicode, hoa thường, khoảng trắng và dấu chấm cuối câu. Review khớp có stance đối lập cho kết quả `mixed`. Thiếu stance rõ ràng cho kết quả `unverified`. |
| `llm_factcheck` | Gemini trích xuất, Fact Check tìm nguồn, Gemini đánh giá. Giữ logic của orchestrator với Tavily bỏ qua. |
| `full` | Orchestrator của backend với Gemini, Fact Check và Tavily. |

Bỏ `--limit` để chạy toàn bộ dataset. Runner thử lại khi chạm quota tối đa hai lần theo mặc định, điều chỉnh bằng `--retries`. Nó dùng `Retry-After` khi có và kết thúc lượt với lỗi quota nếu thời gian chờ vượt 60 giây. Benchmark gọi các provider từ script nên hạn mức của endpoint `/analyze` không áp dụng. `--limit` giới hạn số mẫu của cả bốn chế độ.

## Kết quả và chấm nguồn

Ba file được ghi vào `scripts/benchmark/results/` theo ngày Việt Nam. Dùng `--output-dir` để đổi thư mục.

- `benchmark_<ngày>.md` có bảng chỉ số và ma trận nhầm lẫn theo chế độ. Latency giữ số đo của các lần chạy gốc và loại thời gian ngủ chờ quota. Chi phí dùng cấu hình B1, tính trung bình trên các lượt đủ usage và đơn giá. [Cấu hình số liệu backend](../../backend/README.md#số-liệu-và-phản-hồi)
- `benchmark_<ngày>.csv` có dự đoán, độ trễ, chi phí, trạng thái và cờ cache cho từng mẫu–chế độ.
- `benchmark_<ngày>_citations.csv` có một dòng cho mỗi URL nguồn. Tra `id` trong dataset, rồi điền `true` nếu nguồn thực sự củng cố verdict của dòng đó, `false` nếu không. Để trống khi chưa chấm. Với verdict `false`, nguồn bác bỏ claim là nguồn củng cố verdict. Báo cáo tính tỷ lệ trên các nguồn đã chấm và ghi số nguồn đã chấm trên tổng số nguồn.

Kết quả hoàn tất được lưu ngay vào `scripts/benchmark/.cache/results.db`, riêng với cache C1. Runner gọi orchestrator trực tiếp nên luôn đi qua pipeline khi phải chạy mới. Cache benchmark phân biệt chế độ, SHA-256 của text và cấu hình benchmark. Lượt lỗi hoặc degraded sẽ được thử lại ở lần chạy thường tiếp theo. Dùng `--bypass-cache` để đo lại mà không đọc hoặc ghi cache benchmark, hoặc `--cache` để tạo một cache riêng cho lần chạy mới.

Sau khi chấm, chạy lại cùng dataset và cấu hình với `--cache-only` để cập nhật báo cáo từ cache. Dùng `--judgments path/to/citations.csv` để nhập điểm từ báo cáo ngày khác. Điểm được ghép theo ID, hash văn bản, chế độ, verdict và URL nguồn. File cùng ngày được ghi lại cho tập mẫu đang chạy. Dùng thư mục riêng khi thử một tập con để giữ các phiếu chấm trước đó. Runner trả mã thoát 1 khi có lỗi chạy hoặc thiếu cache, đồng thời vẫn xuất báo cáo cho tập đã yêu cầu.

## Kiểm thử bằng mock

```bash
cd backend
python -m pytest tests/test_benchmark.py
```

Test chạy cả 10 mẫu qua bốn chế độ bằng Gemini SDK mock và HTTP mock. Nó kiểm tra số liệu báo cáo, retry quota và lượt chạy lại với zero API call.
