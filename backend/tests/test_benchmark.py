import asyncio
import csv
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx
from app.core.config import GeminiTokenPrices, settings
from app.prompts.gemini_prompts import ASSESS_PROMPT, EXTRACT_CLAIMS_PROMPT
from app.services.gemini_model_pool import GeminiModelPool, GeminiQuotaExhausted

ROOT = Path(__file__).resolve().parents[2]
FACTCHECK_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
TAVILY_URL = "https://api.tavily.com/search"


@pytest.fixture
def benchmark(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    return importlib.import_module("scripts.benchmark.run_benchmark")


@pytest.fixture
def benchmark_api(monkeypatch, benchmark):
    samples = {
        row.text: row
        for row in benchmark.load_dataset(benchmark.BENCHMARK_DIR / "dataset.csv")
    }
    monkeypatch.setattr(settings, "gemini_api_key", "fake")
    monkeypatch.setattr(settings, "factcheck_api_key", "fake")
    monkeypatch.setattr(settings, "tavily_api_key", "fake")
    monkeypatch.setattr(settings, "gemini_model", "gemini-benchmark-test")
    monkeypatch.setattr(settings, "gemini_models", [])
    monkeypatch.setattr(settings, "search_query_limit", 2)
    monkeypatch.setattr(
        settings,
        "gemini_token_prices",
        {
            "gemini-benchmark-test": GeminiTokenPrices(
                input_usd_per_million=1, output_usd_per_million=2
            )
        },
    )
    monkeypatch.setattr(settings, "tavily_usd_per_credit", 0.01)
    monkeypatch.setattr("app.services.gemini_service.model_pool", GeminiModelPool())

    async def respond(**kwargs):
        assert kwargs["store"] is False
        assert "tools" not in kwargs
        text = kwargs["input"].split("<post>\n", 1)[1].split("\n</post>", 1)[0]
        sample = samples[text]
        prompt = kwargs["system_instruction"]
        if prompt == benchmark.LLM_ONLY_PROMPT:
            assert kwargs["input"] == f"<post>\n{text}\n</post>"
            payload = {"verdict": sample.label}
        elif prompt == EXTRACT_CLAIMS_PROMPT:
            payload = {
                "main_claim": text,
                "search_queries": [text],
                "detected_lang": "vi",
                "is_checkable": True,
            }
        else:
            assert prompt == ASSESS_PROMPT
            payload = {
                "verdict": {"true": "likely_true", "false": "likely_false"}.get(
                    sample.label, sample.label
                ),
                "confidence_score": 0.7,
                "explanation": text,  # Phản hồi có thể lặp lại nguyên văn và không được lưu.
                "source_stances": [],
            }
        return SimpleNamespace(
            output_text=json.dumps(payload),
            usage=SimpleNamespace(total_input_tokens=10, total_output_tokens=5),
        )

    sdk = MagicMock()
    sdk.aio.interactions.create = AsyncMock(side_effect=respond)
    sdk.aio.aclose = AsyncMock()
    sdk_factory = MagicMock(return_value=sdk)
    monkeypatch.setattr("app.services.gemini_service.genai.Client", sdk_factory)
    return sdk_factory, samples


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_sample_end_to_end_resume_and_manual_citations(
    benchmark, benchmark_api, tmp_path
):
    sdk, samples = benchmark_api
    assert len(samples) == 10
    assert {row.topic for row in samples.values()} == benchmark.TOPICS
    assert {row.label for row in samples.values()} == set(benchmark.LABELS)
    output = tmp_path / "reports"
    cache = tmp_path / "cache.db"
    args = ["--output-dir", str(output), "--cache", str(cache), "--limit", "10"]

    def factcheck_response(request):
        text = request.url.params["query"]
        sample = samples[text]
        if sample.label == "unverified":
            return httpx.Response(200, json={"claims": []})
        ratings = {
            "true": ["True"],
            "false": ["Not true"],
            "mixed": ["True", "False"],
        }[sample.label]
        return httpx.Response(
            200,
            json={
                "claims": [
                    {
                        "text": text.upper().rstrip("."),
                        "claimReview": [
                            {
                                "url": f"https://factcheck.org/{sample.id}/{index}",
                                "title": text,
                                "textualRating": rating,
                            }
                            for index, rating in enumerate(ratings)
                        ],
                    },
                    {
                        "text": "Unrelated claim",
                        "claimReview": [
                            {
                                "url": "https://example.com/unrelated",
                                "textualRating": "False",
                            }
                        ],
                    },
                ]
            },
        )

    def tavily_response(request):
        payload = json.loads(request.content)
        sample = samples[payload["query"]]
        assert payload["topic"] == "news"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": sample.text,
                        "url": f"https://reuters.com/{sample.id}",
                        "content": sample.text,
                    }
                ],
                "usage": {"credits": 1},
            },
        )

    with respx.mock(assert_all_called=True) as router:
        factcheck = router.get(FACTCHECK_URL).mock(side_effect=factcheck_response)
        tavily = router.post(TAVILY_URL).mock(side_effect=tavily_response)
        assert benchmark.main(args) == 0

    assert factcheck.call_count == 34
    # Chỉ full gọi Tavily, một lượt cho mỗi mẫu.
    assert tavily.call_count == 10
    assert sdk.return_value.aio.interactions.create.await_count == 48
    sdk.return_value.aio.aclose.assert_awaited_once()
    (report,) = output.glob("benchmark_*.md")
    result_path = report.with_suffix(".csv")
    grade_path = output / f"{report.stem}_citations.csv"
    rows = read_csv(result_path)
    assert len(rows) == 40
    assert all(row["prediction"] == row["label"] and not row["error"] for row in rows)
    assert {row["mode"] for row in rows} == set(benchmark.MODES)
    llm_only = next(row for row in rows if row["mode"] == "llm_only")
    full = next(row for row in rows if row["mode"] == "full")
    assert float(llm_only["estimated_cost_usd"]) == pytest.approx(0.00002)
    assert float(full["estimated_cost_usd"]) == pytest.approx(0.01004)
    assert report.read_text(encoding="utf-8").count("Ma trận nhầm lẫn") == 4
    citations = read_csv(grade_path)
    assert len(citations) == 56
    assert all(not row["supports_verdict"] for row in citations)
    assert not any(
        row["mode"] == "factcheck_only" and row["citation_url"].endswith("/unrelated")
        for row in citations
    )
    assert not any(
        row["mode"] == "llm_factcheck" and "reuters.com" in row["citation_url"]
        for row in citations
    )
    for path in (cache, report, result_path, grade_path):
        contents = path.read_bytes()
        assert all(text.encode() not in contents for text in samples)
        assert b"example.invalid/benchmark/" not in contents

    first, second = (
        row
        for row in citations
        if row["mode"] == "factcheck_only"
        and row["prediction"] == "mixed"
        and row["id"] == "sample-04"
    )
    first["supports_verdict"] = "true"
    second["supports_verdict"] = "false"
    write_csv(grade_path, citations)
    sdk.reset_mock()
    with respx.mock(assert_all_mocked=True) as router:
        assert benchmark.main([*args, "--cache-only"]) == 0
        # Chạy thường cũng phải dùng cache khi mọi cặp đã có.
        assert benchmark.main(args) == 0
        assert router.calls.call_count == 0
    sdk.assert_not_called()
    assert all(row["cached"] == "True" for row in read_csv(result_path))
    assert sorted(
        row["supports_verdict"]
        for row in read_csv(grade_path)
        if row["supports_verdict"]
    ) == ["false", "true"]
    assert "50.0% | 2/10" in report.read_text(encoding="utf-8")


def test_limit_and_http_quota_retry(benchmark, benchmark_api, tmp_path):
    sdk, _ = benchmark_api
    args = [
        "--output-dir",
        str(tmp_path),
        "--cache",
        str(tmp_path / "cache.db"),
        "--limit",
        "1",
    ]
    counts = 0

    def factcheck_response(request):
        nonlocal counts
        counts += 1
        if counts == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(
            200,
            json={
                "claims": [
                    {
                        "text": request.url.params["query"],
                        "claimReview": [
                            {
                                "url": "https://factcheck.org/example",
                                "textualRating": "True",
                            }
                        ],
                    }
                ]
            },
        )

    with respx.mock(assert_all_called=True) as router:
        factcheck = router.get(FACTCHECK_URL).mock(side_effect=factcheck_response)
        tavily = router.post(TAVILY_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {"title": "Reference", "url": "https://reuters.com/example"}
                    ],
                    "usage": {"credits": 1},
                },
            )
        )
        assert benchmark.main(args) == 0
    assert factcheck.call_count == 4
    assert tavily.call_count == 1
    assert sdk.return_value.aio.interactions.create.await_count == 5
    (result_path,) = (
        path for path in tmp_path.glob("*.csv") if "_citations" not in path.name
    )
    rows = read_csv(result_path)
    assert len(rows) == 4
    assert {row["id"] for row in rows} == {"sample-01"}
    assert all(row["prediction"] == "true" for row in rows)


def test_gemini_quota_retry_and_wait_cap(benchmark, monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(benchmark.asyncio, "sleep", sleep)
    sample = benchmark.Sample("test", "Synthetic text", "true", "other", "2026-11-11")
    modes = SimpleNamespace(
        predict=AsyncMock(
            side_effect=[
                GeminiQuotaExhausted(3),
                benchmark.Evaluation(prediction="true"),
            ]
        )
    )
    assert (
        asyncio.run(benchmark.evaluate(modes, "llm_only", sample, 1)).prediction
        == "true"
    )
    sleep.assert_awaited_once_with(3)
    sleep.reset_mock()
    modes.predict = AsyncMock(side_effect=GeminiQuotaExhausted(86400))
    assert (
        asyncio.run(benchmark.evaluate(modes, "llm_only", sample, 2)).error == "quota"
    )
    modes.predict.assert_awaited_once()
    sleep.assert_not_awaited()


def test_empty_cache_only_and_missing_keys_do_not_start_requests(
    benchmark, benchmark_api, tmp_path, monkeypatch
):
    sdk, _ = benchmark_api
    monkeypatch.setattr(settings, "factcheck_api_key", "")
    args = [
        "--output-dir",
        str(tmp_path),
        "--cache",
        str(tmp_path / "empty.db"),
        "--limit",
        "1",
    ]
    with respx.mock(assert_all_mocked=True) as router:
        with pytest.raises(SystemExit) as exit_info:
            benchmark.main(args)
        assert exit_info.value.code == 2
        assert benchmark.main([*args, "--cache-only"]) == 1
        assert router.calls.call_count == 0
    sdk.assert_not_called()
    (result_path,) = (
        path for path in tmp_path.glob("*.csv") if "_citations" not in path.name
    )
    assert {row["error"] for row in read_csv(result_path)} == {"cache_miss"}


def test_metrics_with_incorrect_predictions(benchmark):
    pairs = [
        ("true", "true"),
        ("false", "true"),
        ("mixed", "mixed"),
        ("unverified", "unverified"),
    ]
    rows = [
        benchmark.ResultRow(
            benchmark.Sample(
                str(index), "Synthetic text", actual, "other", "2026-11-11"
            ),
            "full",
            benchmark.Evaluation(
                prediction=predicted,
                latency_ms=index * 10,
                estimated_cost_usd=index if index < 3 else None,
            ),
            False,
        )
        for index, (actual, predicted) in enumerate(pairs, 1)
    ]
    stats = benchmark.summarize(rows)
    assert stats["matrix"]["false", "true"] == 1
    assert stats["accuracy"] == 0.75
    assert stats["macro_f1"] == pytest.approx((2 / 3 + 0 + 1 + 1) / 4)
    assert stats["unverified_rate"] == 0.25
    assert stats["p50_ms"] == 20
    assert stats["p95_ms"] == 40
    assert stats["cost_per_check"] == 1.5
