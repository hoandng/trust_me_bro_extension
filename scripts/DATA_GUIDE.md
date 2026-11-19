# DATA_GUIDE

Đặc tả định dạng dataset CSV và file annotations được nạp bởi `scripts/benchmark/run_benchmark.py`.

Cập nhật theo commit `16c4a3f`, 19/11/2026.

## Cấu trúc file dataset CSV

Hàm `load_dataset()` trong `scripts/benchmark/run_benchmark.py` đọc file UTF-8 (có hỗ trợ BOM `utf-8-sig`) với các cột sau:

| Cột          | Bắt buộc | Quy tắc kiểm tra trong code                                                   | Mô tả                                                               |
| ------------ | -------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `id`         | Có       | Không trống, không trùng lặp trong file                                       | Mã định danh mẫu                                                    |
| `text`       | Có       | Không trống (cắt gọn theo `--max-input-chars`, mặc định `2000`)               | Nội dung claim cần đánh giá                                         |
| `label`      | Có       | Một trong `true`, `false`, `mixed`, `unverified` (không phân biệt hoa/thường) | Nhãn ground truth                                                   |
| `topic`      | Không    | Mặc định `"other"` nếu trống                                                  | Chủ đề mẫu (ví dụ `health`, `scam`, `finance`, `disaster`, `other`) |
| `date`       | Không    | Mặc định `""` nếu trống                                                       | Ngày tham chiếu của claim                                           |
| `source_url` | Không    | `load_dataset()` không đọc cột này                                            | Lưu trữ nguồn tham chiếu phục vụ kiểm tra thủ công                  |

## File annotations tùy chọn

Nếu tồn tại file `<tên_dataset>_annotations.csv` cùng thư mục (hoặc truyền qua `--annotations`), `load_annotations()` tự nạp thêm metadata theo `id`:

- `is_recent`: dùng để tách bảng thống kê phụ trong `report.md` (ví dụ `yes` / `no`).
- `difficulty`: lưu vào đối tượng `Sample` theo từng mẫu.

## Các bộ dữ liệu hiện có trong repo

| File                                                         | Số mẫu | Ghi chú                                                                                   |
| ------------------------------------------------------------ | ------ | ----------------------------------------------------------------------------------------- |
| `scripts/benchmark/dataset_vn_benchmark_100.csv`             | 100    | Dataset mặc định của `run_benchmark.py`, tiếng Việt                                       |
| `scripts/benchmark/dataset_vn_benchmark_100_annotations.csv` | 100    | Bảng annotation (`is_recent`, `difficulty`, `hard_type`, `rationale`, ...) cho bộ 100 mẫu |
| `scripts/benchmark/dataset.csv`                              | 71     | Bộ claim hỗn hợp tiếng Anh và tiếng Việt có kèm `source_url`                              |
| `scripts/benchmark/dataset_vn_excel.csv`                     | —      | Bản CSV xuất từ bảng tính của bộ mẫu tiếng Việt                                           |

## Kiểm tra định dạng dataset

Chạy kiểm tra nạp file mà không gọi API thật (các mẫu chưa có trong cache sẽ báo `cache_miss`):

```bash
python scripts/benchmark/run_benchmark.py --dataset scripts/benchmark/dataset_vn_benchmark_100.csv --cache-only
```

Hướng dẫn chạy đầy đủ xem [scripts/benchmark/README.md](benchmark/README.md).
