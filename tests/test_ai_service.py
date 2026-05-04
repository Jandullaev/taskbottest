"""
tests/test_ai_service.py — Tests for app/services/ai_service.py
Pure logic tests (no network): _safe_json, count_tokens, TokenTracker,
and mocked-AI tests for the higher-level parsing functions.
"""

import pytest
from unittest.mock import patch

from app.services.ai_service import (
    _safe_json,
    count_tokens,
    TokenTracker,
    parse_task_from_text,
    auto_categorize,
    predict_priority,
    generate_daily_motivation,
)


# =============================================================================
#  _safe_json
# =============================================================================

class TestSafeJson:
    def test_valid_json_object(self):
        assert _safe_json('{"key": "value"}') == {"key": "value"}

    def test_json_with_markdown_json_fence(self):
        text = '```json\n{"title": "test"}\n```'
        result = _safe_json(text)
        assert result == {"title": "test"}

    def test_json_with_plain_fence(self):
        text = '```\n{"title": "test"}\n```'
        assert _safe_json(text) == {"title": "test"}

    def test_json_embedded_in_prose(self):
        text = 'Here is the result: {"title": "buy milk"} end.'
        result = _safe_json(text)
        assert result is not None
        assert result["title"] == "buy milk"

    def test_invalid_json_returns_none(self):
        assert _safe_json("this is not json at all") is None

    def test_empty_string_returns_none(self):
        assert _safe_json("") is None

    def test_nested_json(self):
        assert _safe_json('{"a": {"b": 1}}') == {"a": {"b": 1}}

    def test_null_value(self):
        assert _safe_json('{"deadline": null}') == {"deadline": None}

    def test_trailing_backtick_stripped(self):
        result = _safe_json('{"key": "val"}`')
        assert result == {"key": "val"}

    def test_json_with_all_task_fields(self):
        text = '{"title":"Buy milk","description":"","category":"personal","priority":"low","deadline":null}'
        result = _safe_json(text)
        assert result["title"] == "Buy milk"
        assert result["category"] == "personal"
        assert result["deadline"] is None


# =============================================================================
#  count_tokens
# =============================================================================

class TestCountTokens:
    def test_returns_int(self):
        assert isinstance(count_tokens("hello world"), int)

    def test_minimum_one_token(self):
        assert count_tokens("a") >= 1

    def test_empty_string_minimum(self):
        assert count_tokens("") >= 0

    def test_longer_text_more_tokens(self):
        assert count_tokens("short") < count_tokens("This is a much longer sentence with many words")

    def test_approximate_ratio(self):
        # ~1 token per 4 chars: 400 chars ≈ 100 tokens ± 20
        assert 80 <= count_tokens("a" * 400) <= 120

    def test_unicode_text(self):
        # Must not crash on non-ASCII
        result = count_tokens("Привет мир 🌍")
        assert result >= 1


# =============================================================================
#  TokenTracker
# =============================================================================

class TestTokenTracker:
    def test_initial_counts_zero(self):
        t = TokenTracker()
        assert t.total_input_tokens == 0
        assert t.total_output_tokens == 0
        assert t.request_count == 0

    def test_total_tokens_zero_initially(self):
        assert TokenTracker().total_tokens() == 0

    def test_add_accumulates_input(self):
        t = TokenTracker()
        t.add(100, 0)
        t.add(200, 0)
        assert t.total_input_tokens == 300

    def test_add_accumulates_output(self):
        t = TokenTracker()
        t.add(0, 50)
        t.add(0, 100)
        assert t.total_output_tokens == 150

    def test_add_increments_request_count(self):
        t = TokenTracker()
        t.add(10, 10)
        t.add(10, 10)
        assert t.request_count == 2

    def test_total_tokens_sums_input_and_output(self):
        t = TokenTracker()
        t.add(100, 50)
        assert t.total_tokens() == 150

    def test_estimate_cost_keys_present(self):
        t = TokenTracker()
        t.add(1_000_000, 500_000)
        cost = t.estimate_cost()
        assert "input_cost" in cost
        assert "output_cost" in cost
        assert "total_cost" in cost

    def test_estimate_cost_zero_when_no_tokens(self):
        assert TokenTracker().estimate_cost()["total_cost"] == 0.0

    def test_estimate_cost_total_equals_sum(self):
        t = TokenTracker()
        t.add(500_000, 250_000)
        cost = t.estimate_cost()
        assert abs(cost["total_cost"] - (cost["input_cost"] + cost["output_cost"])) < 1e-9

    def test_estimate_cost_proportional_to_tokens(self):
        t1 = TokenTracker()
        t1.add(1000, 0)
        t2 = TokenTracker()
        t2.add(2000, 0)
        assert t2.estimate_cost()["input_cost"] == pytest.approx(
            2 * t1.estimate_cost()["input_cost"]
        )

    def test_get_stats_is_string(self):
        t = TokenTracker()
        t.add(100, 50)
        stats = t.get_stats()
        assert isinstance(stats, str)
        assert len(stats) > 0

    def test_get_stats_contains_request_count(self):
        t = TokenTracker()
        t.add(100, 50)
        assert "1" in t.get_stats()  # request_count == 1


# =============================================================================
#  parse_task_from_text  (mocked _gemini)
# =============================================================================

@pytest.mark.asyncio
async def test_parse_task_returns_dict_on_valid_json():
    payload = '{"title":"Buy milk","description":"","category":"personal","priority":"low","deadline":null}'
    with patch("app.services.ai_service._gemini", return_value=payload):
        result = await parse_task_from_text("Buy milk tomorrow")
    assert result is not None
    assert result["title"] == "Buy milk"
    assert result["category"] == "personal"
    assert result["priority"] == "low"
    assert result["deadline"] is None


@pytest.mark.asyncio
async def test_parse_task_returns_none_on_invalid_json():
    with patch("app.services.ai_service._gemini", return_value="not valid json at all"):
        result = await parse_task_from_text("some task")
    assert result is None


@pytest.mark.asyncio
async def test_parse_task_invalid_category_defaults_to_general():
    payload = '{"title":"Task","description":"","category":"alien","priority":"medium","deadline":null}'
    with patch("app.services.ai_service._gemini", return_value=payload):
        result = await parse_task_from_text("task")
    assert result["category"] == "general"


@pytest.mark.asyncio
async def test_parse_task_invalid_priority_defaults_to_medium():
    payload = '{"title":"Task","description":"","category":"work","priority":"super_urgent","deadline":null}'
    with patch("app.services.ai_service._gemini", return_value=payload):
        result = await parse_task_from_text("task")
    assert result["priority"] == "medium"


@pytest.mark.asyncio
async def test_parse_task_returns_none_on_gemini_exception():
    with patch("app.services.ai_service._gemini", side_effect=Exception("API down")):
        result = await parse_task_from_text("task")
    assert result is None


@pytest.mark.asyncio
async def test_parse_task_deadline_passthrough():
    payload = '{"title":"Task","description":"","category":"work","priority":"high","deadline":"2026-06-01T09:00:00"}'
    with patch("app.services.ai_service._gemini", return_value=payload):
        result = await parse_task_from_text("Submit report by June 1st")
    assert result["deadline"] == "2026-06-01T09:00:00"


@pytest.mark.asyncio
async def test_parse_task_all_valid_categories_accepted():
    for cat in ["work", "study", "personal", "health", "finance", "general"]:
        payload = f'{{"title":"T","description":"","category":"{cat}","priority":"medium","deadline":null}}'
        with patch("app.services.ai_service._gemini", return_value=payload):
            result = await parse_task_from_text("task")
        assert result["category"] == cat


# =============================================================================
#  auto_categorize  (mocked _gemini)
# =============================================================================

@pytest.mark.asyncio
async def test_auto_categorize_valid_category():
    with patch("app.services.ai_service._gemini", return_value="work"):
        assert await auto_categorize("Write quarterly report") == "work"


@pytest.mark.asyncio
async def test_auto_categorize_invalid_defaults_to_general():
    with patch("app.services.ai_service._gemini", return_value="random gibberish"):
        assert await auto_categorize("do something") == "general"


@pytest.mark.asyncio
async def test_auto_categorize_exception_returns_general():
    with patch("app.services.ai_service._gemini", side_effect=Exception("fail")):
        assert await auto_categorize("anything") == "general"


@pytest.mark.asyncio
async def test_auto_categorize_strips_trailing_period():
    with patch("app.services.ai_service._gemini", return_value="study."):
        assert await auto_categorize("homework") == "study"


@pytest.mark.asyncio
async def test_auto_categorize_all_valid_categories():
    for cat in ["work", "study", "personal", "health", "finance", "general"]:
        with patch("app.services.ai_service._gemini", return_value=cat):
            assert await auto_categorize("task") == cat


# =============================================================================
#  predict_priority  (mocked _gemini)
# =============================================================================

@pytest.mark.asyncio
async def test_predict_priority_high():
    with patch("app.services.ai_service._gemini", return_value="high"):
        assert await predict_priority("Fix critical bug") == "high"


@pytest.mark.asyncio
async def test_predict_priority_low():
    with patch("app.services.ai_service._gemini", return_value="low"):
        assert await predict_priority("Someday read this book") == "low"


@pytest.mark.asyncio
async def test_predict_priority_invalid_defaults_to_medium():
    with patch("app.services.ai_service._gemini", return_value="super_urgent"):
        assert await predict_priority("task") == "medium"


@pytest.mark.asyncio
async def test_predict_priority_exception_returns_medium():
    with patch("app.services.ai_service._gemini", side_effect=Exception("fail")):
        assert await predict_priority("task") == "medium"


@pytest.mark.asyncio
async def test_predict_priority_with_deadline():
    with patch("app.services.ai_service._gemini", return_value="high"):
        result = await predict_priority("Critical task", deadline="2026-05-03T09:00:00")
    assert result == "high"


@pytest.mark.asyncio
async def test_predict_priority_all_valid():
    for pri in ["high", "medium", "low"]:
        with patch("app.services.ai_service._gemini", return_value=pri):
            assert await predict_priority("task") == pri


# =============================================================================
#  generate_daily_motivation  (mocked _gemini)
# =============================================================================

@pytest.mark.asyncio
async def test_generate_motivation_returns_response():
    with patch("app.services.ai_service._gemini", return_value="Keep going!"):
        result = await generate_daily_motivation(
            {"pending": 3, "done": 5, "completion_rate": 62, "overdue": 0, "top_category": "work"}
        )
    assert result == "Keep going!"


@pytest.mark.asyncio
async def test_generate_motivation_exception_returns_fallback():
    with patch("app.services.ai_service._gemini", side_effect=Exception("fail")):
        result = await generate_daily_motivation({})
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_generate_motivation_with_empty_stats():
    with patch("app.services.ai_service._gemini", return_value="You got this!"):
        result = await generate_daily_motivation({})
    assert result == "You got this!"
