"""
tests/test_conversations.py — Tests for app/bot/conversations.py.
Covers parse_deadline, wizard inline keyboards, and all conversation
step handlers (addtask, addtask_ai, edittask wizards).
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import InlineKeyboardMarkup
from telegram.ext import ConversationHandler

from app.bot.conversations import (
    parse_deadline,
    _category_inline, _priority_inline, _skip_inline,
    addtask_start, addtask_title, addtask_description,
    addtask_skip_description, addtask_category_inline,
    addtask_priority_inline, addtask_deadline, addtask_skip_deadline,
    _finish_addtask, addtask_cancel,
    addtask_ai_start, addtask_ai_input, addtask_ai_cancel,
    callback_task_edit, callback_edit_field,
    callback_edit_value_inline, edittask_value, _apply_edit,
    edittask_start, edittask_field_text, edittask_cancel,
    _wz_edit,
)
from app.bot.handlers import (
    AT_TITLE, AT_DESCRIPTION, AT_CATEGORY, AT_PRIORITY, AT_DEADLINE,
    AI_INPUT, EDIT_FIELD, EDIT_VALUE,
)


# =============================================================================
#  Mock factories
# =============================================================================

def _sent():
    m = AsyncMock()
    m.chat_id = 1111
    m.chat = AsyncMock()
    m.chat.send_message = AsyncMock(return_value=AsyncMock())
    m.delete = AsyncMock()
    m.edit_text = AsyncMock()
    return m


def _make_msg_update(user_id=1111, text="some text"):
    upd = MagicMock()
    upd.effective_user = MagicMock()
    upd.effective_user.id = user_id
    upd.message = AsyncMock()
    upd.message.text = text
    upd.message.reply_text = AsyncMock(return_value=_sent())
    upd.message.delete = AsyncMock()
    upd.effective_chat = AsyncMock()
    upd.effective_chat.send_message = AsyncMock(return_value=_sent())
    return upd


def _make_cb_update(data="wz_cat_work", user_id=1111):
    upd = MagicMock()
    upd.effective_user = MagicMock()
    upd.effective_user.id = user_id
    upd.callback_query = AsyncMock()
    upd.callback_query.data = data
    upd.callback_query.from_user = MagicMock()
    upd.callback_query.from_user.id = user_id
    upd.callback_query.answer = AsyncMock()
    upd.callback_query.message = _sent()
    return upd


def _make_context(user_data=None, args=None):
    ctx = MagicMock()
    ctx.user_data = dict(user_data) if user_data else {}
    ctx.args = list(args) if args else []
    return ctx


_TASK = {
    "id": 42, "user_id": 1111, "title": "Test task",
    "description": "desc", "status": "pending",
    "category": "work", "priority": "high",
    "deadline": "2026-06-01T09:00:00",
    "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
    "reminded_at": None,
}


# =============================================================================
#  Deadline parser — keyword shortcuts
# =============================================================================

def _freeze(dt):
    return patch("app.bot.conversations.datetime", wraps=datetime,
                 **{"utcnow.return_value": dt})


class TestParseDeadlineKeywords:
    def test_today_defaults_to_0900(self):
        now = datetime(2026, 5, 2, 15, 30, 0)
        with _freeze(now):
            result, err = parse_deadline("today")
        assert err is None
        assert "2026-05-02" in result
        assert "09:00:00" in result

    def test_tomorrow(self):
        now = datetime(2026, 5, 2, 10, 0, 0)
        with _freeze(now):
            result, err = parse_deadline("tomorrow")
        assert err is None
        assert "2026-05-03" in result

    def test_next_week_adds_7_days(self):
        now = datetime(2026, 5, 2, 0, 0, 0)
        with _freeze(now):
            result, err = parse_deadline("next week")
        assert err is None
        expected = (now + timedelta(weeks=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        assert result == expected.isoformat()

    def test_keywords_are_case_insensitive(self):
        now = datetime(2026, 5, 2, 15, 0, 0)
        with _freeze(now):
            r1, _ = parse_deadline("TODAY")
            r2, _ = parse_deadline("TOMORROW")
            r3, _ = parse_deadline("NEXT WEEK")
        assert all(r is not None for r in [r1, r2, r3])


class TestParseDeadlineRelative:
    def test_in_3_days(self):
        now = datetime(2026, 5, 2, 0, 0, 0)
        with _freeze(now):
            result, err = parse_deadline("in 3 days")
        assert err is None
        expected = (now + timedelta(days=3)).replace(hour=9, minute=0, second=0, microsecond=0)
        assert result == expected.isoformat()

    def test_in_1_day(self):
        now = datetime(2026, 5, 2, 0, 0, 0)
        with _freeze(now):
            result, err = parse_deadline("in 1 day")
        assert err is None

    def test_in_2_hours_preserves_time(self):
        now = datetime(2026, 5, 2, 10, 0, 0)
        with _freeze(now):
            result, err = parse_deadline("in 2 hours")
        assert err is None
        expected = (now + timedelta(hours=2)).replace(second=0, microsecond=0)
        assert result == expected.isoformat()

    def test_in_1_hour(self):
        now = datetime(2026, 5, 2, 10, 30, 0)
        with _freeze(now):
            result, err = parse_deadline("in 1 hour")
        assert err is None

    def test_in_1_week(self):
        now = datetime(2026, 5, 2, 0, 0, 0)
        with _freeze(now):
            result, err = parse_deadline("in 1 week")
        assert err is None

    def test_in_3_weeks(self):
        now = datetime(2026, 5, 2, 0, 0, 0)
        with _freeze(now):
            result, err = parse_deadline("in 3 weeks")
        assert err is None


class TestParseDeadlineWeekdays:
    def test_next_monday_from_saturday(self):
        now = datetime(2026, 5, 2, 8, 0, 0)  # Saturday
        with _freeze(now):
            result, err = parse_deadline("next monday")
        assert err is None
        assert "2026-05-04" in result

    def test_all_weekday_names_succeed(self):
        now = datetime(2026, 5, 4, 8, 0, 0)  # Monday
        for day in ["monday", "tuesday", "wednesday", "thursday",
                    "friday", "saturday", "sunday"]:
            with _freeze(now):
                result, err = parse_deadline(day)
            assert err is None, f"Failed for day: {day}"

    def test_weekday_defaults_to_0900(self):
        now = datetime(2026, 5, 4, 8, 0, 0)
        with _freeze(now):
            result, _ = parse_deadline("friday")
        assert "09:00:00" in result

    def test_same_weekday_gives_next_week(self):
        now = datetime(2026, 5, 4, 8, 0, 0)  # Monday
        with _freeze(now):
            result, err = parse_deadline("monday")
        assert err is None
        assert "2026-05-11" in result


class TestParseDeadlineFormats:
    def test_iso_datetime_space(self):
        result, err = parse_deadline("2026-03-15 14:30")
        assert err is None and "2026-03-15" in result and "14:30" in result

    def test_iso_date_only_defaults_to_0900(self):
        result, err = parse_deadline("2026-03-15")
        assert err is None and "09:00:00" in result

    def test_iso_t_separator(self):
        result, err = parse_deadline("2026-03-15T14:30:00")
        assert err is None

    def test_slash_dmy(self):
        result, err = parse_deadline("15/03/2026")
        assert err is None and "2026-03-15" in result

    def test_dot_format(self):
        result, err = parse_deadline("15.03.2026")
        assert err is None and "2026-03-15" in result

    def test_dash_dmy(self):
        result, err = parse_deadline("15-03-2026")
        assert err is None and "2026-03-15" in result

    def test_result_parses_as_isoformat(self):
        result, err = parse_deadline("2026-06-01")
        assert err is None
        datetime.fromisoformat(result)


class TestParseDeadlineErrors:
    def test_garbage_text_returns_error(self):
        result, err = parse_deadline("blahblah123xyz")
        assert result is None and err is not None

    def test_empty_string_returns_error(self):
        result, err = parse_deadline("")
        assert result is None and err is not None

    def test_error_hint_contains_examples(self):
        _, err = parse_deadline("not a date")
        assert err is not None
        assert "tomorrow" in err or "days" in err or "2026" in err


# =============================================================================
#  Wizard step inline keyboards
# =============================================================================

class TestCategoryInline:
    def test_returns_inline_markup(self):
        assert isinstance(_category_inline(), InlineKeyboardMarkup)

    def test_has_all_six_categories(self):
        kb = _category_inline()
        data = [b.callback_data for row in kb.inline_keyboard for b in row]
        for cat in ["work", "study", "personal", "health", "finance", "general"]:
            assert f"wz_cat_{cat}" in data

    def test_exactly_six_buttons(self):
        kb = _category_inline()
        assert sum(len(r) for r in kb.inline_keyboard) == 6


class TestPriorityInline:
    def test_returns_inline_markup(self):
        assert isinstance(_priority_inline(), InlineKeyboardMarkup)

    def test_has_all_three_priorities(self):
        kb = _priority_inline()
        data = [b.callback_data for row in kb.inline_keyboard for b in row]
        for pri in ["high", "medium", "low"]:
            assert f"wz_pri_{pri}" in data


class TestSkipInline:
    def test_returns_inline_markup(self):
        assert isinstance(_skip_inline(), InlineKeyboardMarkup)

    def test_has_skip_button(self):
        kb = _skip_inline()
        data = [b.callback_data for row in kb.inline_keyboard for b in row]
        assert "wz_skip" in data

    def test_exactly_one_button(self):
        assert sum(len(r) for r in _skip_inline().inline_keyboard) == 1


# =============================================================================
#  _wz_edit
# =============================================================================

@pytest.mark.asyncio
async def test_wz_edit_no_wz_msg_is_noop():
    ctx = _make_context()
    await _wz_edit(ctx, "hello")


@pytest.mark.asyncio
async def test_wz_edit_edits_existing_message():
    wz = _sent()
    ctx = _make_context(user_data={"wz_msg": wz})
    await _wz_edit(ctx, "updated text")
    wz.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_wz_edit_fallback_on_edit_failure():
    wz = _sent()
    wz.edit_text.side_effect = Exception("can't edit")
    new_sent = _sent()
    wz.chat.send_message = AsyncMock(return_value=new_sent)
    ctx = _make_context(user_data={"wz_msg": wz})
    await _wz_edit(ctx, "text")
    wz.chat.send_message.assert_called_once()
    assert ctx.user_data["wz_msg"] is new_sent


# =============================================================================
#  addtask wizard
# =============================================================================

@pytest.mark.asyncio
async def test_addtask_start_clears_state_and_returns_at_title():
    upd = _make_msg_update()
    ctx = _make_context(user_data={"new_task": {"old": "data"}})
    result = await addtask_start(upd, ctx)
    assert result == AT_TITLE
    assert "wz_msg" in ctx.user_data
    assert "new_task" not in ctx.user_data


@pytest.mark.asyncio
async def test_addtask_title_saves_title_and_advances():
    upd = _make_msg_update(text="Buy groceries")
    wz = _sent()
    ctx = _make_context(user_data={"wz_msg": wz})
    result = await addtask_title(upd, ctx)
    assert result == AT_DESCRIPTION
    assert ctx.user_data["new_task"]["title"] == "Buy groceries"


@pytest.mark.asyncio
async def test_addtask_description_saves_desc_and_advances():
    upd = _make_msg_update(text="From the supermarket")
    wz = _sent()
    ctx = _make_context(user_data={
        "wz_msg": wz,
        "new_task": {"title": "Buy groceries"},
    })
    result = await addtask_description(upd, ctx)
    assert result == AT_CATEGORY
    assert ctx.user_data["new_task"]["description"] == "From the supermarket"


@pytest.mark.asyncio
async def test_addtask_skip_description_sets_empty_and_advances():
    upd = _make_cb_update(data="wz_skip")
    ctx = _make_context(user_data={"new_task": {"title": "Task"}})
    result = await addtask_skip_description(upd, ctx)
    assert result == AT_CATEGORY
    assert ctx.user_data["new_task"]["description"] == ""


@pytest.mark.asyncio
async def test_addtask_category_inline_saves_category():
    upd = _make_cb_update(data="wz_cat_work")
    ctx = _make_context(user_data={"new_task": {"title": "Task"}})
    result = await addtask_category_inline(upd, ctx)
    assert result == AT_PRIORITY
    assert ctx.user_data["new_task"]["category"] == "work"


@pytest.mark.asyncio
async def test_addtask_category_all_categories_accepted():
    for cat in ["work", "study", "personal", "health", "finance", "general"]:
        upd = _make_cb_update(data=f"wz_cat_{cat}")
        ctx = _make_context(user_data={"new_task": {"title": "T"}})
        result = await addtask_category_inline(upd, ctx)
        assert result == AT_PRIORITY
        assert ctx.user_data["new_task"]["category"] == cat


@pytest.mark.asyncio
async def test_addtask_priority_inline_saves_priority():
    upd = _make_cb_update(data="wz_pri_high")
    ctx = _make_context(user_data={"new_task": {"title": "T", "category": "work"}})
    result = await addtask_priority_inline(upd, ctx)
    assert result == AT_DEADLINE
    assert ctx.user_data["new_task"]["priority"] == "high"


@pytest.mark.asyncio
async def test_addtask_priority_all_priorities():
    for pri in ["high", "medium", "low"]:
        upd = _make_cb_update(data=f"wz_pri_{pri}")
        ctx = _make_context(user_data={"new_task": {"title": "T", "category": "work"}})
        result = await addtask_priority_inline(upd, ctx)
        assert result == AT_DEADLINE
        assert ctx.user_data["new_task"]["priority"] == pri


@pytest.mark.asyncio
async def test_addtask_deadline_invalid_stays_in_state():
    upd = _make_msg_update(text="not a date")
    wz = _sent()
    ctx = _make_context(user_data={"wz_msg": wz, "new_task": {"title": "T"}})
    result = await addtask_deadline(upd, ctx)
    assert result == AT_DEADLINE


@pytest.mark.asyncio
async def test_addtask_deadline_valid_finishes():
    upd = _make_msg_update(text="2026-06-01")
    wz = _sent()
    wz.chat_id = 1111
    ctx = _make_context(user_data={
        "wz_msg": wz,
        "new_task": {"title": "T", "description": "", "category": "work", "priority": "high"},
    })
    with patch("app.bot.conversations.db.create_task", return_value=42), \
         patch("app.bot.conversations.db.get_task", return_value=_TASK):
        result = await addtask_deadline(upd, ctx)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_addtask_skip_deadline_finishes():
    upd = _make_cb_update(data="wz_skip")
    wz = _sent()
    wz.chat_id = 1111
    ctx = _make_context(user_data={
        "wz_msg": wz,
        "new_task": {"title": "T", "description": "", "category": "work", "priority": "high"},
    })
    with patch("app.bot.conversations.db.create_task", return_value=42), \
         patch("app.bot.conversations.db.get_task", return_value=_TASK):
        result = await addtask_skip_deadline(upd, ctx)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_finish_addtask_creates_task_and_ends():
    wz = _sent()
    wz.chat_id = 1111
    ctx = _make_context(user_data={
        "wz_msg": wz,
        "new_task": {"title": "T", "description": "", "category": "work", "priority": "high"},
    })
    with patch("app.bot.conversations.db.create_task", return_value=42), \
         patch("app.bot.conversations.db.get_task", return_value=_TASK):
        result = await _finish_addtask(None, ctx, "2026-06-01T09:00:00")
    assert result == ConversationHandler.END
    assert ctx.user_data.get("current_task_id") == 42


@pytest.mark.asyncio
async def test_addtask_cancel_clears_state():
    upd = _make_msg_update()
    wz = _sent()
    ctx = _make_context(user_data={"wz_msg": wz, "new_task": {"title": "T"}})
    result = await addtask_cancel(upd, ctx)
    assert result == ConversationHandler.END
    assert "new_task" not in ctx.user_data
    assert "wz_msg" not in ctx.user_data


@pytest.mark.asyncio
async def test_addtask_cancel_no_wz_msg():
    upd = _make_msg_update()
    ctx = _make_context()
    result = await addtask_cancel(upd, ctx)
    assert result == ConversationHandler.END


# =============================================================================
#  addtask_ai wizard
# =============================================================================

@pytest.mark.asyncio
async def test_addtask_ai_start_returns_ai_input():
    upd = _make_msg_update()
    ctx = _make_context()
    result = await addtask_ai_start(upd, ctx)
    assert result == AI_INPUT
    assert "wz_msg" in ctx.user_data


@pytest.mark.asyncio
async def test_addtask_ai_input_success_ends():
    upd = _make_msg_update(text="Submit report by Friday")
    wz = _sent()
    ctx = _make_context(user_data={"wz_msg": wz})
    parsed = {"title": "Submit report", "description": "",
              "category": "work", "priority": "high", "deadline": None}
    with patch("app.bot.conversations.db.get_user", return_value={"timezone": "UTC"}), \
         patch("app.bot.conversations.ai.parse_task_from_text", return_value=parsed), \
         patch("app.bot.conversations.db.create_task", return_value=42), \
         patch("app.bot.conversations.db.get_task", return_value=_TASK):
        result = await addtask_ai_input(upd, ctx)
    assert result == ConversationHandler.END
    assert ctx.user_data.get("current_task_id") == 42


@pytest.mark.asyncio
async def test_addtask_ai_input_parse_failure_ends():
    upd = _make_msg_update(text="???")
    wz = _sent()
    ctx = _make_context(user_data={"wz_msg": wz})
    with patch("app.bot.conversations.db.get_user", return_value={"timezone": "UTC"}), \
         patch("app.bot.conversations.ai.parse_task_from_text", return_value=None):
        result = await addtask_ai_input(upd, ctx)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_addtask_ai_cancel_clears_state():
    upd = _make_msg_update()
    wz = _sent()
    ctx = _make_context(user_data={"wz_msg": wz})
    result = await addtask_ai_cancel(upd, ctx)
    assert result == ConversationHandler.END
    assert "wz_msg" not in ctx.user_data


# =============================================================================
#  edittask wizard
# =============================================================================

@pytest.mark.asyncio
async def test_edittask_start_no_args_ends():
    upd = _make_msg_update()
    ctx = _make_context(args=[])
    result = await edittask_start(upd, ctx)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_edittask_start_invalid_id_ends():
    upd = _make_msg_update()
    ctx = _make_context(args=["abc"])
    result = await edittask_start(upd, ctx)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_edittask_start_task_not_found_ends():
    upd = _make_msg_update()
    ctx = _make_context(args=["99"])
    with patch("app.bot.conversations.db.get_task", return_value=None):
        result = await edittask_start(upd, ctx)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_edittask_start_found_returns_edit_field():
    upd = _make_msg_update(user_id=1111)
    ctx = _make_context(args=["1"])
    with patch("app.bot.conversations.db.get_task", return_value=_TASK):
        result = await edittask_start(upd, ctx)
    assert result == EDIT_FIELD
    assert ctx.user_data["edit_id"] == 1


@pytest.mark.asyncio
async def test_callback_task_edit_returns_edit_field():
    upd = _make_cb_update(data="task_edit_42")
    ctx = _make_context()
    result = await callback_task_edit(upd, ctx)
    assert result == EDIT_FIELD
    assert ctx.user_data["edit_id"] == 42


@pytest.mark.asyncio
async def test_callback_task_edit_invalid_data():
    upd = _make_cb_update(data="task_edit_abc")
    ctx = _make_context()
    result = await callback_task_edit(upd, ctx)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_callback_edit_field_title():
    upd = _make_cb_update(data="ef_title")
    ctx = _make_context(user_data={"edit_id": 1})
    result = await callback_edit_field(upd, ctx)
    assert result == EDIT_VALUE
    assert ctx.user_data["edit_field"] == "title"


@pytest.mark.asyncio
async def test_callback_edit_field_all_fields():
    for field in ["title", "description", "category", "priority", "deadline", "status"]:
        upd = _make_cb_update(data=f"ef_{field}")
        ctx = _make_context(user_data={"edit_id": 1})
        result = await callback_edit_field(upd, ctx)
        assert result == EDIT_VALUE
        assert ctx.user_data["edit_field"] == field


@pytest.mark.asyncio
async def test_callback_edit_value_category():
    upd = _make_cb_update(data="wz_cat_study")
    ctx = _make_context(user_data={
        "edit_id": 1, "edit_user_id": 1111, "edit_field": "category",
        "edit_orig_msg": _sent(),
    })
    with patch("app.bot.conversations.db.update_task", return_value=True), \
         patch("app.bot.conversations.db.get_task", return_value=_TASK):
        result = await callback_edit_value_inline(upd, ctx)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_callback_edit_value_priority():
    upd = _make_cb_update(data="wz_pri_low")
    ctx = _make_context(user_data={
        "edit_id": 1, "edit_user_id": 1111, "edit_field": "priority",
        "edit_orig_msg": _sent(),
    })
    with patch("app.bot.conversations.db.update_task", return_value=True), \
         patch("app.bot.conversations.db.get_task", return_value=_TASK):
        result = await callback_edit_value_inline(upd, ctx)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_callback_edit_value_status():
    upd = _make_cb_update(data="ef_val_done")
    ctx = _make_context(user_data={
        "edit_id": 1, "edit_user_id": 1111, "edit_field": "status",
        "edit_orig_msg": _sent(),
    })
    with patch("app.bot.conversations.db.update_task", return_value=True), \
         patch("app.bot.conversations.db.get_task", return_value=_TASK):
        result = await callback_edit_value_inline(upd, ctx)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_callback_edit_value_skip():
    upd = _make_cb_update(data="wz_skip")
    ctx = _make_context(user_data={
        "edit_id": 1, "edit_user_id": 1111, "edit_field": "description",
        "edit_orig_msg": _sent(),
    })
    with patch("app.bot.conversations.db.update_task", return_value=True), \
         patch("app.bot.conversations.db.get_task", return_value=_TASK):
        result = await callback_edit_value_inline(upd, ctx)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_edittask_value_title():
    upd = _make_msg_update(text="New title")
    orig = _sent()
    ctx = _make_context(user_data={
        "edit_id": 1, "edit_user_id": 1111, "edit_field": "title",
        "edit_orig_msg": orig,
    })
    with patch("app.bot.conversations.db.update_task", return_value=True), \
         patch("app.bot.conversations.db.get_task", return_value=_TASK):
        result = await edittask_value(upd, ctx)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_edittask_value_deadline_invalid_stays():
    upd = _make_msg_update(text="not a date")
    orig = _sent()
    ctx = _make_context(user_data={
        "edit_id": 1, "edit_user_id": 1111, "edit_field": "deadline",
        "edit_orig_msg": orig,
    })
    result = await edittask_value(upd, ctx)
    assert result == EDIT_VALUE


@pytest.mark.asyncio
async def test_edittask_value_deadline_valid():
    upd = _make_msg_update(text="2026-06-01")
    orig = _sent()
    ctx = _make_context(user_data={
        "edit_id": 1, "edit_user_id": 1111, "edit_field": "deadline",
        "edit_orig_msg": orig,
    })
    with patch("app.bot.conversations.db.update_task", return_value=True), \
         patch("app.bot.conversations.db.get_task", return_value=_TASK):
        result = await edittask_value(upd, ctx)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_apply_edit_success():
    orig = _sent()
    ctx = _make_context(user_data={
        "edit_id": 1, "edit_user_id": 1111, "edit_field": "title",
    })
    with patch("app.bot.conversations.db.update_task", return_value=True), \
         patch("app.bot.conversations.db.get_task", return_value=_TASK):
        result = await _apply_edit(orig, ctx, "New title")
    assert result == ConversationHandler.END
    assert "edit_id" not in ctx.user_data


@pytest.mark.asyncio
async def test_apply_edit_failure():
    orig = _sent()
    ctx = _make_context(user_data={
        "edit_id": 1, "edit_user_id": 1111, "edit_field": "title",
    })
    with patch("app.bot.conversations.db.update_task", return_value=False), \
         patch("app.bot.conversations.db.get_task", return_value=None):
        result = await _apply_edit(orig, ctx, "New title")
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_edittask_field_text_sets_field_and_advances():
    upd = _make_msg_update(text="Title")
    orig = _sent()
    ctx = _make_context(user_data={"edit_id": 1, "edit_orig_msg": orig})
    result = await edittask_field_text(upd, ctx)
    assert result == EDIT_VALUE
    assert ctx.user_data["edit_field"] == "title"


@pytest.mark.asyncio
async def test_edittask_field_text_all_fields():
    for field in ["title", "description", "category", "priority", "deadline", "status"]:
        upd = _make_msg_update(text=field.capitalize())
        orig = _sent()
        ctx = _make_context(user_data={"edit_id": 1, "edit_orig_msg": orig})
        result = await edittask_field_text(upd, ctx)
        assert result == EDIT_VALUE
        assert ctx.user_data["edit_field"] == field


@pytest.mark.asyncio
async def test_edittask_cancel_clears_state():
    upd = _make_msg_update()
    orig = _sent()
    ctx = _make_context(user_data={
        "edit_orig_msg": orig, "edit_id": 1,
        "edit_user_id": 1111, "edit_field": "title",
    })
    result = await edittask_cancel(upd, ctx)
    assert result == ConversationHandler.END
    assert "edit_id" not in ctx.user_data
    assert "edit_field" not in ctx.user_data


@pytest.mark.asyncio
async def test_edittask_cancel_no_orig_msg():
    upd = _make_msg_update()
    ctx = _make_context()
    result = await edittask_cancel(upd, ctx)
    assert result == ConversationHandler.END
