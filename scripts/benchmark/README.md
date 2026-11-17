# Benchmark kiểm chứng (3 chế độ)

Script `run_benchmark.py` so sánh 3 chế độ để trả lời câu hỏi hệ thống có **đáng dùng hơn chatbot Gemini thông thường** và **Tavily có đáng tiền** hay không:

| Chế độ | Luồng xử lý |
|---|---|
| `llm_only` | Gemini trả lời trực tiếp bằng kiến thức sẵn có (tương tự chatbot Gemini, không dùng công cụ tìm kiếm). |
| `llm_factcheck` | Pipeline `AnalysisOrchestrator` với Gemini + Google Fact Check (tắt Tavily). |
| `full` | Pipeline đầy đủ của hệ thống: Gemini + Google Fact Check + Tavily Search. |

## Cách chạy

Chạy từ thư mục gốc (cần cấu hình `GEMINI_API_KEY`, `FACTCHECK_API_KEY`, `TAVILY_API_KEY` trong `backend/.env`):

```bash
# Chạy thử 10 mẫu đầu trên bộ dataset 100 mẫu
python scripts/benchmark/run_benchmark.py --dataset scripts/benchmark/dataset_vn_benchmark_100.csv --limit 10

# Chạy toàn bộ với giới hạn tốc độ gọi API để tránh 429
python scripts/benchmark/run_benchmark.py --dataset scripts/benchmark/dataset_vn_benchmark_100.csv --rpm 15
```

Các tùy chọn chống lỗi API phổ biến:
- `--rpm` / `--min-interval` / `--sample-delay`: điều tiết tốc độ gọi API và tự động giãn cách khi gặp `429 Too Many Requests`.
- `--retries`, `--http-retries`, `--transient-retries`, `--max-wait`: thử lại theo `Retry-After` + exponential backoff; tự dừng sớm nếu chạm quota ngày (`retry_after > max-wait`) mà vẫn lưu kết quả đã chạy.
- `--max-input-chars` (mặc định `2000`), `max_output_tokens`, `thinking_level=low`: giới hạn độ dài đầu vào/đầu ra để tránh lỗi quá token hoặc cắt cụt JSON.
- `--gemini-timeout` (mặc định `30s`) và `--timeout` (mặc định `45s`): tránh timeout giả khi mạng chậm.
- Cache resume (`scripts/benchmark/.cache/results_v2.db`): lưu ngay mỗi lượt thành công (không lưu lỗi/degraded), chạy lại sẽ tự tiếp tục từ phần còn thiếu. Dùng `--bypass-cache` để đo mới hoàn toàn hoặc `--cache-only` để xuất lại báo cáo từ cache.

## Kết quả đầu ra

Mỗi lần chạy tạo một thư mục riêng theo giờ Việt Nam (`UTC+7`):

`scripts/benchmark/results/<tên_file_dataset>_<DD-MM-YYYY>_<HH-MM-SS>/`

Bên trong gồm 4 file:
- `report.md`: bảng so sánh 3 chế độ (Macro-F1 kèm 95% Bootstrap CI, Accuracy, Lỗi nghiêm trọng, Unverified, $/lượt, p50/p95), kiểm định McNemar, kết luận **Đáng sử dụng / Cần cải thiện**, bảng phụ `is_recent` (nếu có file `*_annotations.csv`) và ma trận nhầm lẫn.
- `raw.csv`: dữ liệu chi tiết cho từng cặp mẫu × chế độ.
- `chart.png`: biểu đồ Macro-F1 theo chi phí mỗi lượt.
- `summary.json`: số liệu tổng hợp dạng JSON.

## Kiểm thử bằng mock

```bash
cd backend
python -m pytest tests/test_benchmark.py
```
