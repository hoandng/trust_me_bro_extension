# Benchmark kiểm chứng (3 chế độ)

Hướng dẫn chạy script `scripts/benchmark/run_benchmark.py` để so sánh độ chính xác, chi phí và độ trễ giữa 3 chế độ kiểm chứng.

Cập nhật theo commit `f491d97`, 20/11/2026.

## Các chế độ so sánh

| Chế độ          | Luồng xử lý                                                                                   |
| --------------- | --------------------------------------------------------------------------------------------- |
| `llm_only`      | Gemini đánh giá trực tiếp bằng `LLM_ONLY_PROMPT`, không dùng công cụ tìm kiếm                 |
| `llm_factcheck` | `AnalysisOrchestrator` chạy Gemini + Google Fact Check (thay Tavily bằng `NullTavilyService`) |
| `full`          | Pipeline đầy đủ: Gemini + Google Fact Check + Tavily Search                                   |

## Cách chạy

Chạy từ thư mục gốc sau khi cấu hình `GEMINI_API_KEY`, `FACTCHECK_API_KEY` và `TAVILY_API_KEY` trong `backend/.env` (các lệnh dưới gọi API thật và tiêu tốn hạn mức, trừ `--cache-only`):

```bash
# Chạy thử 10 mẫu đầu trên bộ 100 mẫu tiếng Việt
python scripts/benchmark/run_benchmark.py --dataset scripts/benchmark/dataset_vn_benchmark_100.csv --limit 10

# Chạy toàn bộ có điều tiết RPM
python scripts/benchmark/run_benchmark.py --dataset scripts/benchmark/dataset_vn_benchmark_100.csv --rpm 15

# Xuất lại báo cáo từ cache (không gọi API)
python scripts/benchmark/run_benchmark.py --dataset scripts/benchmark/dataset_vn_benchmark_100.csv --cache-only
```

Các tùy chọn chính (`python scripts/benchmark/run_benchmark.py --help`):

- `--dataset`: đường dẫn CSV dataset (mặc định `scripts/benchmark/dataset_vn_benchmark_100.csv`, fallback `dataset.csv`).
- `--annotations`: file CSV annotation tùy chọn (tự nạp `<stem>_annotations.csv` nếu tồn tại).
- `--modes`: chọn tập con trong `llm_only`, `llm_factcheck`, `full`; `--limit`, `--repeats`, `--model`, `--allow-fallback`.
- `--rpm`, `--min-interval` (`1.0s`), `--sample-delay` (`0.5s`): điều tiết tốc độ gọi Gemini.
- `--retries` (`3`), `--http-retries` (`3`), `--transient-retries` (`2`), `--max-wait` (`90.0s`), `--no-stop-on-daily-quota`: xử lý `429` và lỗi tạm thời.
- `--gemini-timeout` (`30.0s`), `--timeout` (`45.0s`), `--max-input-chars` (`2000`): giới hạn thời gian và độ dài đầu vào.
- `--cache` (mặc định `scripts/benchmark/.cache/results_v2.db`), `--bypass-cache`, `--cache-only`: cơ chế lưu resume (chỉ lưu lượt không lỗi và không degraded; không lưu văn bản gốc).
- `--gemini-input-price`, `--gemini-output-price`, `--tavily-credit-price`: ghi đè đơn giá tham chiếu USD.

## Kết quả đầu ra

Mỗi lần chạy tạo thư mục `scripts/benchmark/results/<tên_dataset>_<DD-MM-YYYY>_<HH-MM-SS>/` theo giờ `Asia/Ho_Chi_Minh` gồm 4 file:

- `report.md`: bảng Macro-F1 (95% Bootstrap CI), Accuracy, lỗi nghiêm trọng, tỷ lệ `unverified`, chi phí, p50/p95, kiểm định McNemar, phân rã thời gian từng bước và ma trận nhầm lẫn.
- `raw.csv`: kết quả chi tiết từng cặp mẫu × chế độ.
- `chart.png`: biểu đồ Macro-F1 theo chi phí (sinh khi `matplotlib` khả dụng).
- `summary.json`: toàn bộ số liệu tổng hợp dạng JSON.

Xem đặc tả cấu trúc CSV tại [DATA_GUIDE.md](../DATA_GUIDE.md).

## Kiểm thử bằng mock

```bash
cd backend
pytest tests/test_benchmark.py
```
