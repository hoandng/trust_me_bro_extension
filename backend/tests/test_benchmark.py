import asyncio
import csv
import importlib
import json
import re
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
    mod = importlib.import_module("scripts.benchmark.run_benchmark")
    return importlib.reload(mod)


@pytest.fixture
def benchmark_api(monkeypatch, benchmark):
    samples = {
        row.text: row
        for row in benchmark.load_dataset(benchmark.BENCHMARK_DIR / "dataset.csv")
    }
    monkeypatch.setattr(settings, "gemini_api_key", "fake")
    monkeypatch.setattr(settings, "factcheck_api_key", "fake")
    monkeypatch.setattr(settings, "tavily_api_key", "fake")
    monkeypatch.setattr(settings, "gemini_model", "gemini-3.1-flash-lite")
    monkeypatch.setattr(settings, "gemini_models", [])
    monkeypatch.setattr(settings, "search_query_limit", 2)
    monkeypatch.setattr(
        settings,
        "gemini_token_prices",
        {
            "gemini-3.1-flash-lite": GeminiTokenPrices(
                input_usd_per_million=1.0, output_usd_per_million=2.0
            )
        },
    )
    monkeypatch.setattr(settings, "tavily_usd_per_credit", 0.005)
    monkeypatch.setattr("app.services.gemini_service.model_pool", GeminiModelPool())

    async def respond(**kwargs):
        assert kwargs["store"] is False
        assert "tools" not in kwargs
        gen_cfg = kwargs["generation_config"]
        assert gen_cfg["temperature"] == 0.0
        assert gen_cfg["thinking_level"] == "low"
        assert gen_cfg["max_output_tokens"] >= 1024

        text = kwargs["input"].split("<post>\n", 1)[1].split("\n</post>", 1)[0]
        sample = samples[text]
        prompt = kwargs["system_instruction"]
        if prompt == benchmark.LLM_ONLY_PROMPT:
            payload = {
                "verdict": {"true": "likely_true", "false": "likely_false"}.get(
                    sample.label, sample.label
                ),
                "confidence_score": 0.8,
                "explanation": "Synthetic explanation",
            }
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
                "confidence_score": 0.85,
                "explanation": "Synthetic assessment",
                "source_stances": [],
            }
        return SimpleNamespace(
            output_text=json.dumps(payload),
            usage=SimpleNamespace(total_input_tokens=100, total_output_tokens=50),
        )

    sdk = MagicMock()
    sdk.aio.interactions.create = AsyncMock(side_effect=respond)
    sdk.aio.aclose = AsyncMock()
    sdk_factory = MagicMock(return_value=sdk)
    monkeypatch.setattr("app.services.gemini_service.genai.Client", sdk_factory)
    return sdk_factory, samples


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def test_end_to_end_3_modes_output_naming_and_cache_resume(
    benchmark, benchmark_api, tmp_path
):
    sdk, samples = benchmark_api
    assert len(samples) == 10
    output = tmp_path / "results"
    cache = tmp_path / "cache.db"
    dataset_path = benchmark.BENCHMARK_DIR / "dataset.csv"
    args = [
        "--dataset",
        str(dataset_path),
        "--output-dir",
        str(output),
        "--cache",
        str(cache),
        "--limit",
        "4",
        "--min-interval",
        "0",
        "--sample-delay",
        "0",
    ]

    def factcheck_response(request):
        text = request.url.params["query"]
        sample = samples[text]
        if sample.label == "unverified":
            return httpx.Response(200, json={"claims": []})
        return httpx.Response(
            200,
            json={
                "claims": [
                    {
                        "text": text,
                        "claimReview": [
                            {
                                "url": f"https://factcheck.org/{sample.id}",
                                "title": "Fact Check Review",
                                "textualRating": "True"
                                if sample.label == "true"
                                else "False",
                            }
                        ],
                    }
                ]
            },
        )

    def tavily_response(request):
        payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "News Article",
                        "url": f"https://reuters.com/{hash(payload['query']) % 1000}",
                        "content": "Supporting evidence.",
                    }
                ],
                "usage": {"credits": 1},
            },
        )

    with respx.mock(assert_all_called=True) as router:
        factcheck = router.get(FACTCHECK_URL).mock(side_effect=factcheck_response)
        tavily = router.post(TAVILY_URL).mock(side_effect=tavily_response)
        assert benchmark.main(args) == 0

    assert factcheck.call_count >= 8
    assert tavily.call_count == 4
    # 4 llm_only + 7 llm_factcheck (sample-03 skips assess when 0 sources) + 8 full = 19 calls
    assert sdk.return_value.aio.interactions.create.await_count == 19

    run_dirs = sorted(output.iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert re.fullmatch(r"dataset_\d{2}-\d{2}-\d{4}_\d{2}-\d{2}-\d{2}", run_dir.name)

    for fname in ("report.md", "raw.csv", "summary.json", "chart.png"):
        assert (run_dir / fname).is_file(), f"Missing {fname}"

    rows = read_csv(run_dir / "raw.csv")
    assert len(rows) == 12
    assert {r["mode"] for r in rows} == set(benchmark.MODES)
    assert all(r["prediction"] == r["label"] and not r["error"] for r in rows)

    # Privacy check: raw post text and dataset source URLs must not be saved in outputs/cache
    for path in (
        cache,
        run_dir / "raw.csv",
        run_dir / "report.md",
        run_dir / "summary.json",
    ):
        blob = path.read_bytes()
        assert all(text.encode() not in blob for text in samples)
        assert b"example.invalid/benchmark/" not in blob

    # Cache-only and resume run must make zero Gemini API / HTTP calls
    sdk.return_value.aio.interactions.create.reset_mock()
    with respx.mock(assert_all_mocked=True) as router:
        assert benchmark.main([*args, "--cache-only"]) == 0
        assert benchmark.main(args) == 0
        assert router.calls.call_count == 0
    sdk.return_value.aio.interactions.create.assert_not_awaited()


def test_http_429_retry_and_daily_quota_abort(
    benchmark, benchmark_api, tmp_path, monkeypatch
):
    _sdk, _ = benchmark_api
    monkeypatch.setattr(benchmark.asyncio, "sleep", AsyncMock())

    counts = 0

    def factcheck_429_then_ok(request):
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
                            {"url": "https://factcheck.org/1", "textualRating": "True"}
                        ],
                    }
                ]
            },
        )

    args = [
        "--dataset",
        str(benchmark.BENCHMARK_DIR / "dataset.csv"),
        "--output-dir",
        str(tmp_path / "results"),
        "--cache",
        str(tmp_path / "cache.db"),
        "--modes",
        "llm_factcheck",
        "--limit",
        "1",
        "--min-interval",
        "0",
        "--sample-delay",
        "0",
    ]
    with respx.mock(assert_all_called=True) as router:
        fc = router.get(FACTCHECK_URL).mock(side_effect=factcheck_429_then_ok)
        assert benchmark.main(args) == 0
        assert fc.call_count == 2

    # Daily quota error (> max_wait) stops cleanly and returns exit code 1
    sample = benchmark.Sample("id-1", "Text", "true", "other", "2026-11-17")
    with pytest.raises(benchmark.DailyQuotaExhausted):
        asyncio.run(
            benchmark.evaluate_with_retry(
                mode="llm_only",
                sample=sample,
                repeat=1,
                model="gemini-3.1-flash-lite",
                max_retries=2,
                max_wait_seconds=60.0,
                gemini=SimpleNamespace(
                    classify_chatbot=AsyncMock(side_effect=GeminiQuotaExhausted(86400)),
                    last_sleep_seconds=0.0,
                ),
                factcheck_orch=None,
                full_orch=None,
                gemini_input_price=None,
                gemini_output_price=None,
                tavily_credit_price=None,
            )
        )


def test_truncate_text_and_metrics_summary(benchmark):
    long_text = " ".join(["token"] * 600)
    trimmed = benchmark.truncate_text(long_text, 200)
    assert len(trimmed) <= 200
    assert trimmed.endswith("...")

    # Create paired rows where full outperforms llm_only significantly
    rows = []
    for i in range(20):
        gold = ["true", "false", "mixed", "unverified"][i % 4]
        is_recent = "yes" if i < 10 else "no"
        # llm_only gets 5/20 right and makes critical errors
        llm_pred = gold if i < 5 else ("false" if gold == "true" else "true")
        # full gets 19/20 right and 0 critical errors
        full_pred = gold if i < 19 else "unverified"
        rows.append(
            benchmark.EvaluationRow(
                id=f"s-{i}",
                mode="llm_only",
                repeat=1,
                label=gold,
                topic="other",
                is_recent=is_recent,
                prediction=llm_pred,
                correct=(llm_pred == gold),
                critical_error=(
                    (gold == "true" and llm_pred == "false")
                    or (gold == "false" and llm_pred == "true")
                ),
                confidence_score=0.7,
                n_sources=0,
                factcheck_hits=0,
                tavily_hits=0,
                latency_ms=1500.0,
                extract_ms=None,
                evidence_ms=None,
                assess_ms=None,
                input_tokens=100,
                output_tokens=40,
                thought_tokens=0,
                cached_tokens=0,
                total_tokens=140,
                gemini_calls=1,
                factcheck_calls=0,
                tavily_credits=0,
                estimated_cost_usd=0.0001,
                models_used="gemini-3.1-flash-lite",
                quota_retries=0,
            )
        )
        rows.append(
            benchmark.EvaluationRow(
                id=f"s-{i}",
                mode="full",
                repeat=1,
                label=gold,
                topic="other",
                is_recent=is_recent,
                prediction=full_pred,
                correct=(full_pred == gold),
                critical_error=False,
                confidence_score=0.9,
                n_sources=2,
                factcheck_hits=0,
                tavily_hits=2,
                latency_ms=4200.0,
                extract_ms=1000,
                evidence_ms=1500,
                assess_ms=1700,
                input_tokens=1000,
                output_tokens=200,
                thought_tokens=0,
                cached_tokens=0,
                total_tokens=1200,
                gemini_calls=2,
                factcheck_calls=1,
                tavily_credits=1,
                estimated_cost_usd=0.0085,
                models_used="gemini-3.1-flash-lite",
                quota_retries=0,
            )
        )

    out_dir = Path("tmp_test_report_unused")
    del out_dir  # we test pure functions directly
    summaries = {
        m: benchmark.summarize_mode([r for r in rows if r.mode == m])
        for m in ("llm_only", "full")
    }
    mc = benchmark.exact_mcnemar(
        [r for r in rows if r.mode == "llm_only"],
        [r for r in rows if r.mode == "full"],
    )
    worth = benchmark.evaluate_worth_using(summaries, mc)
    assert mc["b_improved"] == 15
    assert mc["c_regressed"] == 0
    assert mc["p_value"] < 0.05
    assert worth["verdict"] == "ĐÁNG SỬ DỤNG"

    md = benchmark.build_report_markdown(
        dataset_name="test.csv",
        n_samples=20,
        model="gemini-3.1-flash-lite",
        run_ts="17-11-2026 09:20:00",
        rows=rows,
        summaries=summaries,
        mc_full_llm=mc,
        mc_full_fc={"b_improved": 0, "c_regressed": 0, "p_value": 1.0},
        worth=worth,
        used_fallback_price=False,
    )
    assert "is_recent=yes" in md
    assert "ĐÁNG SỬ DỤNG" in md
