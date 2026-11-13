"""Sinh dataset benchmark bằng Gemini, dùng Tavily để gắn source_url thật.

Chiến lược:
  1. Với mỗi (topic, label), yêu cầu Gemini sinh N claim ngắn gọn, tự nhiên
     như bài đăng Facebook tiếng Việt.
  2. Dùng Tavily tìm URL thật cho mỗi claim (dùng làm source_url tham chiếu).
  3. Xuất ra CSV hợp lệ sẵn sàng để chạy run_benchmark.py.

Chạy:
  cd <project-root>
  python scripts/benchmark/generate_dataset.py --out scripts/benchmark/dataset_real.csv

Yêu cầu: GEMINI_API_KEY và TAVILY_API_KEY trong backend/.env
"""

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import date
from itertools import product
from pathlib import Path

import httpx
from dotenv import load_dotenv


BENCHMARK_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BENCHMARK_DIR.parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or ""
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY") or ""
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

LABELS = ("true", "false", "mixed", "unverified")
TOPICS = ("health", "scam", "finance", "disaster", "other")

# Số claim Gemini sinh mỗi (topic, label). Tổng = PER_SLOT * 4 * 5 = 20*20 = 100 mẫu
PER_SLOT = 5

TOPIC_VI = {
    "health": "sức khỏe, y tế, thuốc, dinh dưỡng, dịch bệnh",
    "scam": "lừa đảo trực tuyến, tin nhắn giả mạo, OTP, giải thưởng giả, mạo danh ngân hàng hoặc cơ quan nhà nước",
    "finance": "tài chính cá nhân, lãi suất, chứng khoán, tiền điện tử, giá vàng, bất động sản",
    "disaster": "thiên tai, bão lũ, động đất, cháy rừng, sự cố môi trường tại Việt Nam",
    "other": "khoa học tổng quát, địa lý, lịch sử, giáo dục, công nghệ thông thường",
}

LABEL_VI = {
    "true": (
        "hoàn toàn ĐÚNG và có thể kiểm chứng bằng nguồn báo chí hay tổ chức uy tín. "
        "Claim nên cụ thể, có số liệu hoặc sự kiện rõ ràng."
    ),
    "false": (
        "hoàn toàn SAI về mặt thực tế — thông tin bịa đặt, con số sai, hoặc "
        "mâu thuẫn rõ ràng với kiến thức phổ thông. KHÔNG dùng mệnh đề phủ định rõ ràng; "
        "hãy để claim nghe có vẻ hợp lý nhưng thực ra sai."
    ),
    "mixed": (
        "MIXED — kết hợp một phần đúng và một phần sai trong cùng một câu, "
        "ví dụ: sự kiện có thật nhưng số liệu bị cường điệu, hoặc kết luận sai từ dữ liệu đúng."
    ),
    "unverified": (
        "KHÔNG THỂ XÁC MINH qua nguồn công khai — sự kiện siêu cục bộ, tin đồn chưa rõ, "
        "dự đoán tương lai, hoặc tuyên bố cá nhân không có bằng chứng."
    ),
}

SYSTEM_PROMPT = """\
Bạn là chuyên gia tạo dữ liệu huấn luyện cho hệ thống fact-checking tiếng Việt.
Nhiệm vụ: sinh {n} câu claim ngắn (1–3 câu, tối đa 150 ký tự mỗi claim) bắt chước
phong cách bài đăng Facebook hoặc caption tin tức tiếng Việt về chủ đề: {topic_desc}.

Mỗi claim phải: {label_desc}

Yêu cầu chất lượng:
- Dùng ngôn ngữ tự nhiên, không học thuật quá
- Đa dạng về cấu trúc câu và từ ngữ
- KHÔNG lặp lại ý tưởng giữa các claim
- KHÔNG chứa tên người thật hoặc địa chỉ cụ thể dễ gây tranh cãi pháp lý
- Với label "false": claim phải nghe có vẻ hợp lý nhưng thực ra sai

Trả về JSON hợp lệ, không có text nào khác:
{{"claims": ["claim 1", "claim 2", ...]}}
"""


async def generate_claims(
    client: httpx.AsyncClient,
    topic: str,
    label: str,
    n: int,
) -> list[str]:
    """Gọi Gemini để sinh danh sách claim."""
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": SYSTEM_PROMPT.format(
                            n=n,
                            topic_desc=TOPIC_VI[topic],
                            label_desc=LABEL_VI[label],
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 1.0,
            "maxOutputTokens": 2048,
        },
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    resp = await client.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(text)
    return [c.strip() for c in data.get("claims", []) if c.strip()]


async def find_source_url(
    client: httpx.AsyncClient,
    claim: str,
    topic: str,
) -> str:
    """Dùng Tavily tìm URL thật liên quan đến claim; trả fallback nếu không tìm được."""
    fallback = f"https://example.invalid/benchmark/{topic}"
    if not TAVILY_API_KEY:
        return fallback
    try:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": claim,
                "search_depth": "basic",
                "max_results": 1,
                "include_domains": [
                    # Ưu tiên nguồn uy tín Việt Nam và quốc tế
                    "vnexpress.net",
                    "tuoitre.vn",
                    "nhandan.vn",
                    "who.int",
                    "moh.gov.vn",
                    "sbv.gov.vn",
                    "reuters.com",
                    "bbc.com",
                ],
            },
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if results:
            return results[0].get("url", fallback)
    except Exception:  # noqa: BLE001
        pass
    return fallback


def build_sample_id(topic: str, label: str, index: int) -> str:
    label_abbr = {"true": "T", "false": "F", "mixed": "M", "unverified": "U"}
    return f"{topic[:3].upper()}-{label_abbr[label]}-{index:03d}"


async def run(out_path: Path, per_slot: int, skip_tavily: bool) -> None:
    if not GEMINI_API_KEY:
        sys.exit("❌ Thiếu GEMINI_API_KEY trong backend/.env")

    today = date.today().isoformat()
    rows: list[dict] = []
    index = 1

    async with httpx.AsyncClient() as client:
        for topic, label in product(TOPICS, LABELS):
            print(f"  → Đang sinh {per_slot} claim [{topic}/{label}]...")
            try:
                claims = await generate_claims(client, topic, label, per_slot)
            except Exception as e:  # noqa: BLE001
                print(f"    ⚠️  Lỗi khi sinh claim: {e}")
                continue

            for claim in claims[:per_slot]:
                if skip_tavily:
                    url = f"https://example.invalid/benchmark/{topic}"
                else:
                    url = await find_source_url(client, claim, topic)

                rows.append(
                    {
                        "id": build_sample_id(topic, label, index),
                        "text": claim,
                        "label": label,
                        "topic": topic,
                        "source_url": url,
                        "date": today,
                    }
                )
                index += 1

    # Ghi CSV
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "text", "label", "topic", "source_url", "date"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ Đã sinh {len(rows)} mẫu → {out_path}")
    print("\nPhân phối nhãn:")
    from collections import Counter

    for label, count in sorted(Counter(r["label"] for r in rows).items()):
        print(f"  {label:12s}: {count}")
    print("\nPhân phối topic:")
    for topic, count in sorted(Counter(r["topic"] for r in rows).items()):
        print(f"  {topic:12s}: {count}")
    print("\nBước tiếp theo:")
    print(f"  1. Mở {out_path.name} và review thủ công (đặc biệt cột 'label')")
    print("  2. Thay source_url example.invalid bằng URL thật nếu cần")
    print(
        f"  3. Chạy: python scripts/benchmark/run_benchmark.py --dataset {out_path.name}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=BENCHMARK_DIR / "dataset_generated.csv",
        help="Đường dẫn file CSV đầu ra",
    )
    parser.add_argument(
        "--per-slot",
        type=int,
        default=PER_SLOT,
        help=f"Số claim mỗi (topic, label). Mặc định {PER_SLOT}. "
        f"Tổng = per_slot × 4 × 5",
    )
    parser.add_argument(
        "--skip-tavily",
        action="store_true",
        help="Bỏ qua tìm URL thật (dùng example.invalid). Nhanh hơn khi không có TAVILY_API_KEY.",
    )
    args = parser.parse_args()

    if args.per_slot <= 0:
        parser.error("--per-slot phải lớn hơn 0")

    total = args.per_slot * len(LABELS) * len(TOPICS)
    print(
        f"🚀 Đang sinh dataset: {args.per_slot} claim × {len(LABELS)} nhãn × {len(TOPICS)} topic = {total} mẫu"
    )
    print(f"   Gemini model : {GEMINI_MODEL}")
    print(
        f"   Tìm URL thật : {'Tắt (--skip-tavily)' if args.skip_tavily else 'Bật (Tavily)'}\n"
    )

    asyncio.run(run(args.out, args.per_slot, args.skip_tavily))


if __name__ == "__main__":
    main()
