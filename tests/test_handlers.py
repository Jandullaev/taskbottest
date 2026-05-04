"""
tests/test_handlers.py — Comprehensive tests for app/bot/handlers.py.
Covers _delete, _safe_edit, all command handlers, menu handlers,
task action handlers, and inline callbacks using mocked Telegram objects.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from telegram.error import BadRequest
from telegram.ext import ConversationHandler

from app.bot.handlers import (
    _delete, _safe_edit,
    cmd_start, cmd_help, cmd_mytasks, cmd_mytask, cmd_done,
    cmd_deletetask, cmd_stats, cmd_settimezone,
    msg_handle_menu_mytasks, msg_handle_menu_stats,
    msg_handle_menu_filters, msg_handle_filter,
    msg_handle_menu_timezone, msg_handle_timezone,
    msg_back_to_menu, _render_task_list,
    msg_handle_task_done, msg_handle_task_edit,
    msg_handle_task_delete, msg_handle_task_delete_confirm,
    msg_handle_task_delete_cancel,
    callback_task_view, callback_main_menu,
    unknown_command,
    AT_TITLE, EDIT_FIELD, _TIMEZONE_MAP, _FILTER_MAP, EDIT_FIELDS,
)


# =============================================================================
#  Mock factories
# =============================================================================

def _sent():
    """A mock message as returned by send_message / reply_text."""
    m = AsyncMock()
    m.chat_id = 1111
    m.chat = AsyncMock()
    m.chat.send_message = AsyncMock(return_value=AsyncMock())
    m.delete = AsyncMock()
    m.edit_text = AsyncMock()
    return m


def _make_update(user_id=1111, text="", username="tester", full_name="Tester User"):
    upd = MagicMock()
    upd.effective_user = MagicMock()
    upd.effective_user.id = user_id
    upd.effective_user.username = username
    upd.effective_user.full_name = full_name
    upd.effective_user.first_name = "Tester"

    sent_msg = _sent()
    upd.message = AsyncMock()
    upd.message.text = text
    upd.message.reply_text = AsyncMock(return_value=sent_msg)
    upd.message.delete = AsyncMock()

    upd.effective_chat = AsyncMock()
    upd.effective_chat.send_message = AsyncMock(return_value=sent_msg)
    return upd


def _make_cb_update(data="task_view_1", user_id=1111):
    upd = MagicMock()
    upd.effective_user = MagicMock()
    upd.effective_user.id = user_id

    upd.callback_query = AsyncMock()
    upd.callback_query.data = data
    upd.callback_query.from_user = MagicMock()
    upd.callback_query.from_user.id = user_id
    upd.callback_query.answer = AsyncMock()

    sent_msg = _sent()
    upd.callback_query.message = AsyncMock()
    upd.callback_query.message.chat = AsyncMock()
    upd.callback_query.message.chat.send_message = AsyncMock(return_value=sent_msg)
    upd.callback_query.message.delete = AsyncMock()
    upd.callback_query.message.edit_text = AsyncMock()
    return upd


def _make_context(user_data=None, args=None):
    ctx = MagicMock()
    ctx.user_data = dict(user_data) if user_data else {}
    ctx.args = list(args) if args else []
    return ctx


_TASK = {
    "id": 1, "user_id": 1111, "title": "Test task",
    "description": "desc", "status": "pending",
    "category": "work", "priority": "high",
    "deadline": "2026-06-01T09:00:00",
    "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
    "reminded_at": None,
}
_STATS = {
    "total": 5, "done": 3, "pending": 2, "overdue": 0,
    "completion_rate": 60.0, "top_category": "work",
}
_USER_ROW = {
    "user_id": 1111, "username": "tester",
    "full_name": "Tester User", "timezone": "UTC",
}


# =============================================================================
#  _delete
# =============================================================================

@pytest.mark.asyncio
async def test_delete_none_is_noop():
    await _delete(None)


@pytest.mark.asyncio
async def test_delete_calls_message_delete():
    msg = AsyncMock()
    await _delete(msg)
    msg.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_swallows_exception():
    msg = AsyncMock()
    msg.delete.side_effect = Exception("already deleted")
    await _delete(msg)


@pytest.mark.asyncio
async def test_delete_swallows_bad_request():
    msg = AsyncMock()
    msg.delete.side_effect = BadRequest("Message to delete not found")
    await _delete(msg)


# =============================================================================
#  _safe_edit
# =============================================================================

@pytest.mark.asyncio
async def test_safe_edit_calls_edit_text():
    msg = AsyncMock()
    await _safe_edit(msg, "hello")
    msg.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_safe_edit_passes_reply_markup():
    msg = AsyncMock()
    markup = MagicMock()
    await _safe_edit(msg, "text", reply_markup=markup)
    _, kwargs = msg.edit_text.call_args
    assert kwargs.get("reply_markup") == markup


@pytest.mark.asyncio
async def test_safe_edit_swallows_not_modified():
    msg = AsyncMock()
    msg.edit_text.side_effect = BadRequest("Message is not modified")
    await _safe_edit(msg, "same text")


@pytest.mark.asyncio
async def test_safe_edit_swallows_cant_be_edited():
    msg = AsyncMock()
    msg.edit_text.side_effect = BadRequest("Message can't be edited")
    await _safe_edit(msg, "old")


@pytest.mark.asyncio
async def test_safe_edit_swallows_can_not_be_edited():
    msg = AsyncMock()
    msg.edit_text.side_effect = BadRequest("Message can not be edited")
    await _safe_edit(msg, "old")


@pytest.mark.asyncio
async def test_safe_edit_reraises_other_bad_request():
    msg = AsyncMock()
    msg.edit_text.side_effect = BadRequest("Something else")
    with pytest.raises(BadRequest):
        await _safe_edit(msg, "text")


@pytest.mark.asyncio
async def test_safe_edit_swallows_cant_edited_uppercase():
    msg = AsyncMock()
    msg.edit_text.side_effect = BadRequest("MESSAGE CAN'T BE EDITED")
    await _safe_edit(msg, "text")


# =============================================================================
#  State constants / maps
# =============================================================================

def test_conversation_states_are_unique():
    from app.bot.handlers import (
        AT_TITLE, AT_DESCRIPTION, AT_CATEGORY, AT_PRIORITY, AT_DEADLINE,
        AI_INPUT, EDIT_FIELD, EDIT_VALUE,
    )
    states = [AT_TITLE, AT_DESCRIPTION, AT_CATEGORY, AT_PRIORITY, AT_DEADLINE,
              AI_INPUT, EDIT_FIELD, EDIT_VALUE]
    assert len(states) == len(set(states))


def test_edit_fields_complete():
    assert set(EDIT_FIELDS) == {"Title", "Description", "Category", "Priority", "Deadline", "Status"}


def test_timezone_map_utc():
    assert _TIMEZONE_MAP["🌍 UTC"] == "UTC"


def test_timezone_map_tashkent():
    assert _TIMEZONE_MAP["🌍 Tashkent"] == "Asia/Tashkent"


def test_filter_map_status_filters():
    statuses = {v[1] for v in _FILTER_MAP.values() if v[0] == "status"}
    assert {"pending", "done", "in_progress"}.issubset(statuses)


def test_filter_map_category_filters():
    categories = {v[1] for v in _FILTER_MAP.values() if v[0] == "category"}
    assert {"work", "study", "personal", "health", "finance"}.issubset(categories)


def test_filter_map_tuple_format():
    for key, val in _FILTER_MAP.items():
        assert isinstance(val, tuple) and len(val) == 2
        assert val[0] in ("status", "category")


# =============================================================================
#  cmd_start
# =============================================================================

@pytest.mark.asyncio
async def test_cmd_start_upserts_user():
    upd = _make_update(user_id=999, username="alice", full_name="Alice")
    ctx = _make_context()
    with patch("app.bot.handlers.db.upsert_user", new_callable=AsyncMock) as mock_up:
        await cmd_start(upd, ctx)
    mock_up.assert_called_once_with(999, "alice", "Alice")


@pytest.mark.asyncio
async def test_cmd_start_sends_welcome():
    upd = _make_update()
    ctx = _make_context()
    with patch("app.bot.handlers.db.upsert_user", new_callable=AsyncMock):
        await cmd_start(upd, ctx)
    upd.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_cmd_start_username_none_uses_empty():
    upd = _make_update()
    upd.effective_user.username = None
    ctx = _make_context()
    with patch("app.bot.handlers.db.upsert_user", new_callable=AsyncMock) as mock_up:
        await cmd_start(upd, ctx)
    args = mock_up.call_args[0]
    assert args[1] == ""


@pytest.mark.asyncio
async def test_cmd_start_full_name_none_uses_first_name():
    upd = _make_update()
    upd.effective_user.full_name = None
    upd.effective_user.first_name = "Bob"
    ctx = _make_context()
    with patch("app.bot.handlers.db.upsert_user", new_callable=AsyncMock) as mock_up:
        await cmd_start(upd, ctx)
    args = mock_up.call_args[0]
    assert args[2] == "Bob"


# =============================================================================
#  cmd_help
# =============================================================================

@pytest.mark.asyncio
async def test_cmd_help_sends_reply():
    upd = _make_update()
    ctx = _make_context()
    await cmd_help(upd, ctx)
    upd.message.reply_text.assert_called_once()


# =============================================================================
#  msg_handle_menu_mytasks
# =============================================================================

@pytest.mark.asyncio
async def test_menu_mytasks_renders_list():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    with patch("app.bot.handlers.db.get_user_tasks", return_value=[_TASK]):
        await msg_handle_menu_mytasks(upd, ctx)
    upd.effective_chat.send_message.assert_called()


@pytest.mark.asyncio
async def test_menu_mytasks_stores_menu_msg():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    with patch("app.bot.handlers.db.get_user_tasks", return_value=[]):
        await msg_handle_menu_mytasks(upd, ctx)
    assert "menu_msg" in ctx.user_data


# =============================================================================
#  msg_handle_menu_stats
# =============================================================================

@pytest.mark.asyncio
async def test_menu_stats_with_user():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    with patch("app.bot.handlers.db.get_user", return_value=_USER_ROW), \
         patch("app.bot.handlers.db.get_user_stats", return_value=_STATS), \
         patch("app.bot.handlers.ai.generate_daily_motivation", return_value="Go!"):
        await msg_handle_menu_stats(upd, ctx)
    assert upd.effective_chat.send_message.call_count >= 2


@pytest.mark.asyncio
async def test_menu_stats_user_none_uses_default_name():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    with patch("app.bot.handlers.db.get_user", return_value=None), \
         patch("app.bot.handlers.db.get_user_stats", return_value=_STATS), \
         patch("app.bot.handlers.ai.generate_daily_motivation", return_value="Go!"):
        await msg_handle_menu_stats(upd, ctx)
    upd.effective_chat.send_message.assert_called()


# =============================================================================
#  msg_handle_menu_filters
# =============================================================================

@pytest.mark.asyncio
async def test_menu_filters_clears_task_state():
    upd = _make_update()
    ctx = _make_context(user_data={"current_task_id": 5, "active_msg": MagicMock()})
    await msg_handle_menu_filters(upd, ctx)
    assert "current_task_id" not in ctx.user_data
    assert "active_msg" not in ctx.user_data


@pytest.mark.asyncio
async def test_menu_filters_sends_filter_keyboard():
    upd = _make_update()
    ctx = _make_context()
    await msg_handle_menu_filters(upd, ctx)
    upd.effective_chat.send_message.assert_called_once()
    assert "menu_msg" in ctx.user_data


# =============================================================================
#  msg_handle_filter
# =============================================================================

@pytest.mark.asyncio
async def test_handle_filter_status_pending():
    upd = _make_update(text="⏳ Pending")
    ctx = _make_context()
    with patch("app.bot.handlers.db.get_user_tasks", return_value=[_TASK]):
        await msg_handle_filter(upd, ctx)
    upd.effective_chat.send_message.assert_called()


@pytest.mark.asyncio
async def test_handle_filter_category_work():
    upd = _make_update(text="💼 Work")
    ctx = _make_context()
    with patch("app.bot.handlers.db.get_user_tasks", return_value=[]):
        await msg_handle_filter(upd, ctx)


@pytest.mark.asyncio
async def test_handle_filter_unknown_button_returns_early():
    upd = _make_update(text="🤷 Unknown")
    ctx = _make_context()
    await msg_handle_filter(upd, ctx)
    upd.effective_chat.send_message.assert_not_called()


# =============================================================================
#  msg_handle_menu_timezone
# =============================================================================

@pytest.mark.asyncio
async def test_menu_timezone_sends_keyboard():
    upd = _make_update()
    ctx = _make_context()
    await msg_handle_menu_timezone(upd, ctx)
    upd.effective_chat.send_message.assert_called_once()
    assert "menu_msg" in ctx.user_data


# =============================================================================
#  msg_handle_timezone
# =============================================================================

@pytest.mark.asyncio
async def test_handle_timezone_valid():
    upd = _make_update(text="🌍 UTC")
    ctx = _make_context(user_data={"user_id": 1111})
    with patch("app.bot.handlers.db.update_user_preferences", new_callable=AsyncMock):
        await msg_handle_timezone(upd, ctx)
    upd.effective_chat.send_message.assert_called()


@pytest.mark.asyncio
async def test_handle_timezone_unknown_button():
    upd = _make_update(text="🌍 NotACity")
    ctx = _make_context()
    await msg_handle_timezone(upd, ctx)
    call_text = upd.effective_chat.send_message.call_args[0][0]
    assert "Invalid" in call_text or "invalid" in call_text.lower()


@pytest.mark.asyncio
async def test_handle_timezone_pytz_error():
    upd = _make_update(text="🌍 UTC")
    ctx = _make_context()
    with patch("app.bot.handlers.pytz.timezone", side_effect=Exception("bad tz")), \
         patch("app.bot.handlers.db.update_user_preferences", new_callable=AsyncMock):
        await msg_handle_timezone(upd, ctx)
    upd.effective_chat.send_message.assert_called()


# =============================================================================
#  msg_back_to_menu
# =============================================================================

@pytest.mark.asyncio
async def test_back_to_menu_sends_message():
    upd = _make_update()
    ctx = _make_context()
    await msg_back_to_menu(upd, ctx)
    upd.effective_chat.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_back_to_menu_deletes_active_msg():
    upd = _make_update()
    active = AsyncMock()
    ctx = _make_context(user_data={"active_msg": active})
    await msg_back_to_menu(upd, ctx)
    active.delete.assert_called_once()
    assert "active_msg" not in ctx.user_data


# =============================================================================
#  _render_task_list
# =============================================================================

@pytest.mark.asyncio
async def test_render_task_list_no_tasks_sends_clear_message():
    msg = _sent()
    with patch("app.bot.handlers.db.get_user_tasks", return_value=[]):
        await _render_task_list(msg, 1111)
    msg.chat.send_message.assert_called_once()
    text = msg.chat.send_message.call_args[0][0]
    assert "No tasks" in text


@pytest.mark.asyncio
async def test_render_task_list_with_tasks_edits_message():
    msg = _sent()
    with patch("app.bot.handlers.db.get_user_tasks", return_value=[_TASK]):
        await _render_task_list(msg, 1111)
    msg.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_render_task_list_status_label():
    msg = _sent()
    with patch("app.bot.handlers.db.get_user_tasks", return_value=[_TASK]):
        await _render_task_list(msg, 1111, status="pending")
    text = msg.edit_text.call_args[0][0]
    assert "Pending" in text


@pytest.mark.asyncio
async def test_render_task_list_category_label():
    msg = _sent()
    with patch("app.bot.handlers.db.get_user_tasks", return_value=[_TASK]):
        await _render_task_list(msg, 1111, category="work")
    text = msg.edit_text.call_args[0][0]
    assert "Work" in text


# =============================================================================
#  cmd_mytasks
# =============================================================================

@pytest.mark.asyncio
async def test_cmd_mytasks_no_args_no_tasks():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    with patch("app.bot.handlers.db.get_user_tasks", return_value=[]):
        await cmd_mytasks(upd, ctx)
    upd.message.reply_text.assert_called_once()
    text = upd.message.reply_text.call_args[0][0]
    assert "No tasks" in text


@pytest.mark.asyncio
async def test_cmd_mytasks_no_args_with_tasks():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    with patch("app.bot.handlers.db.get_user_tasks", return_value=[_TASK]):
        await cmd_mytasks(upd, ctx)
    upd.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_cmd_mytasks_with_status_arg():
    upd = _make_update(user_id=1111)
    ctx = _make_context(args=["pending"])
    with patch("app.bot.handlers.db.get_user_tasks", return_value=[_TASK]) as mock_get:
        await cmd_mytasks(upd, ctx)
    mock_get.assert_called_once_with(1111, status="pending", category=None)


@pytest.mark.asyncio
async def test_cmd_mytasks_with_category_arg():
    upd = _make_update(user_id=1111)
    ctx = _make_context(args=["work"])
    with patch("app.bot.handlers.db.get_user_tasks", return_value=[_TASK]) as mock_get:
        await cmd_mytasks(upd, ctx)
    mock_get.assert_called_once_with(1111, status=None, category="work")


@pytest.mark.asyncio
async def test_cmd_mytasks_unknown_arg_no_filter():
    upd = _make_update(user_id=1111)
    ctx = _make_context(args=["garbage"])
    with patch("app.bot.handlers.db.get_user_tasks", return_value=[]) as mock_get:
        await cmd_mytasks(upd, ctx)
    mock_get.assert_called_once_with(1111, status=None, category=None)


# =============================================================================
#  cmd_mytask
# =============================================================================

@pytest.mark.asyncio
async def test_cmd_mytask_no_args_sends_usage():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    await cmd_mytask(upd, ctx)
    upd.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_cmd_mytask_invalid_id_returns():
    upd = _make_update(user_id=1111)
    ctx = _make_context(args=["abc"])
    await cmd_mytask(upd, ctx)
    upd.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_cmd_mytask_not_found():
    upd = _make_update(user_id=1111)
    ctx = _make_context(args=["99"])
    with patch("app.bot.handlers.db.get_task", return_value=None):
        await cmd_mytask(upd, ctx)
    upd.message.reply_text.assert_called_once()
    text = upd.message.reply_text.call_args[0][0]
    assert "not found" in text


@pytest.mark.asyncio
async def test_cmd_mytask_found_sends_task_card():
    upd = _make_update(user_id=1111)
    ctx = _make_context(args=["1"])
    with patch("app.bot.handlers.db.get_task", return_value=_TASK):
        await cmd_mytask(upd, ctx)
    upd.message.reply_text.assert_called_once()
    assert ctx.user_data["current_task_id"] == 1


# =============================================================================
#  callback_task_view
# =============================================================================

@pytest.mark.asyncio
async def test_callback_task_view_found():
    upd = _make_cb_update(data="task_view_1", user_id=1111)
    ctx = _make_context()
    with patch("app.bot.handlers.db.get_task", return_value=_TASK):
        await callback_task_view(upd, ctx)
    upd.callback_query.answer.assert_called_once()
    assert ctx.user_data["current_task_id"] == 1


@pytest.mark.asyncio
async def test_callback_task_view_not_found():
    upd = _make_cb_update(data="task_view_99", user_id=1111)
    ctx = _make_context()
    with patch("app.bot.handlers.db.get_task", return_value=None):
        await callback_task_view(upd, ctx)
    upd.callback_query.answer.assert_called_with("Task not found.", show_alert=True)


@pytest.mark.asyncio
async def test_callback_task_view_invalid_data():
    upd = _make_cb_update(data="task_view_abc", user_id=1111)
    ctx = _make_context()
    await callback_task_view(upd, ctx)
    upd.callback_query.answer.assert_called_with("Invalid request.", show_alert=True)


# =============================================================================
#  msg_handle_task_done
# =============================================================================

@pytest.mark.asyncio
async def test_handle_task_done_no_task_id_routes_to_filter():
    upd = _make_update(text="✅ Done", user_id=1111)
    ctx = _make_context()
    with patch("app.bot.handlers.db.get_user_tasks", return_value=[]):
        await msg_handle_task_done(upd, ctx)


@pytest.mark.asyncio
async def test_handle_task_done_task_not_found():
    upd = _make_update(user_id=1111)
    ctx = _make_context(user_data={"current_task_id": 1})
    with patch("app.bot.handlers.db.get_task", return_value=None):
        await msg_handle_task_done(upd, ctx)
    upd.effective_chat.send_message.assert_called()
    assert "current_task_id" not in ctx.user_data


@pytest.mark.asyncio
async def test_handle_task_done_already_done():
    upd = _make_update(user_id=1111)
    done_task = {**_TASK, "status": "done"}
    ctx = _make_context(user_data={"current_task_id": 1})
    with patch("app.bot.handlers.db.get_task", return_value=done_task):
        await msg_handle_task_done(upd, ctx)
    text = upd.effective_chat.send_message.call_args[0][0]
    assert "already" in text


@pytest.mark.asyncio
async def test_handle_task_done_marks_done():
    upd = _make_update(user_id=1111)
    done_task = {**_TASK, "status": "done"}
    ctx = _make_context(user_data={"current_task_id": 1})
    with patch("app.bot.handlers.db.get_task", side_effect=[_TASK, done_task]), \
         patch("app.bot.handlers.db.update_task", new_callable=AsyncMock):
        await msg_handle_task_done(upd, ctx)
    upd.effective_chat.send_message.assert_called()
    assert ctx.user_data["current_task_id"] == 1


# =============================================================================
#  msg_handle_task_edit
# =============================================================================

@pytest.mark.asyncio
async def test_handle_task_edit_no_task_id():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    result = await msg_handle_task_edit(upd, ctx)
    assert result == ConversationHandler.END
    upd.effective_chat.send_message.assert_called()


@pytest.mark.asyncio
async def test_handle_task_edit_task_not_found():
    upd = _make_update(user_id=1111)
    ctx = _make_context(user_data={"current_task_id": 1})
    with patch("app.bot.handlers.db.get_task", return_value=None):
        result = await msg_handle_task_edit(upd, ctx)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_task_edit_opens_field_selector():
    upd = _make_update(user_id=1111)
    ctx = _make_context(user_data={"current_task_id": 1})
    with patch("app.bot.handlers.db.get_task", return_value=_TASK):
        result = await msg_handle_task_edit(upd, ctx)
    assert result == EDIT_FIELD
    assert ctx.user_data["edit_id"] == 1


# =============================================================================
#  msg_handle_task_delete
# =============================================================================

@pytest.mark.asyncio
async def test_handle_task_delete_no_task_id():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    await msg_handle_task_delete(upd, ctx)
    text = upd.effective_chat.send_message.call_args[0][0]
    assert "No task" in text


@pytest.mark.asyncio
async def test_handle_task_delete_task_not_found():
    upd = _make_update(user_id=1111)
    ctx = _make_context(user_data={"current_task_id": 1})
    with patch("app.bot.handlers.db.get_task", return_value=None):
        await msg_handle_task_delete(upd, ctx)
    upd.effective_chat.send_message.assert_called()


@pytest.mark.asyncio
async def test_handle_task_delete_shows_confirm():
    upd = _make_update(user_id=1111)
    ctx = _make_context(user_data={"current_task_id": 1})
    with patch("app.bot.handlers.db.get_task", return_value=_TASK):
        await msg_handle_task_delete(upd, ctx)
    upd.effective_chat.send_message.assert_called()
    assert ctx.user_data.get("delete_task_id") == 1


# =============================================================================
#  msg_handle_task_delete_confirm
# =============================================================================

@pytest.mark.asyncio
async def test_handle_delete_confirm_no_task_id():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    await msg_handle_task_delete_confirm(upd, ctx)
    text = upd.effective_chat.send_message.call_args[0][0]
    assert "No task" in text


@pytest.mark.asyncio
async def test_handle_delete_confirm_success():
    upd = _make_update(user_id=1111)
    ctx = _make_context(user_data={"delete_task_id": 1, "current_task_id": 1})
    with patch("app.bot.handlers.db.delete_task", return_value=True):
        await msg_handle_task_delete_confirm(upd, ctx)
    text = upd.effective_chat.send_message.call_args[0][0]
    assert "deleted" in text
    assert "current_task_id" not in ctx.user_data


@pytest.mark.asyncio
async def test_handle_delete_confirm_failure():
    upd = _make_update(user_id=1111)
    ctx = _make_context(user_data={"delete_task_id": 1})
    with patch("app.bot.handlers.db.delete_task", return_value=False):
        await msg_handle_task_delete_confirm(upd, ctx)
    text = upd.effective_chat.send_message.call_args[0][0]
    assert "Could not" in text


# =============================================================================
#  msg_handle_task_delete_cancel
# =============================================================================

@pytest.mark.asyncio
async def test_handle_delete_cancel_no_task_id():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    await msg_handle_task_delete_cancel(upd, ctx)
    upd.effective_chat.send_message.assert_called()


@pytest.mark.asyncio
async def test_handle_delete_cancel_task_not_found():
    upd = _make_update(user_id=1111)
    ctx = _make_context(user_data={"delete_task_id": 1})
    with patch("app.bot.handlers.db.get_task", return_value=None):
        await msg_handle_task_delete_cancel(upd, ctx)
    upd.effective_chat.send_message.assert_called()


@pytest.mark.asyncio
async def test_handle_delete_cancel_restores_task_card():
    upd = _make_update(user_id=1111)
    ctx = _make_context(user_data={"delete_task_id": 1, "current_task_id": 1})
    with patch("app.bot.handlers.db.get_task", return_value=_TASK):
        await msg_handle_task_delete_cancel(upd, ctx)
    upd.effective_chat.send_message.assert_called()
    assert ctx.user_data["current_task_id"] == 1
    assert "delete_task_id" not in ctx.user_data


# =============================================================================
#  cmd_done
# =============================================================================

@pytest.mark.asyncio
async def test_cmd_done_no_args_sends_usage():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await cmd_done(upd, ctx)
    upd.effective_chat.send_message.assert_called()


@pytest.mark.asyncio
async def test_cmd_done_invalid_id():
    upd = _make_update(user_id=1111)
    ctx = _make_context(args=["abc"])
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await cmd_done(upd, ctx)
    upd.effective_chat.send_message.assert_called()


@pytest.mark.asyncio
async def test_cmd_done_task_not_found():
    upd = _make_update(user_id=1111)
    ctx = _make_context(args=["42"])
    with patch("asyncio.sleep", new_callable=AsyncMock), \
         patch("app.bot.handlers.db.get_task", return_value=None):
        await cmd_done(upd, ctx)
    upd.effective_chat.send_message.assert_called()


@pytest.mark.asyncio
async def test_cmd_done_marks_task_done():
    upd = _make_update(user_id=1111)
    ctx = _make_context(args=["1"])
    done_task = {**_TASK, "status": "done"}
    with patch("app.bot.handlers.db.get_task", side_effect=[_TASK, done_task]), \
         patch("app.bot.handlers.db.update_task", new_callable=AsyncMock):
        await cmd_done(upd, ctx)
    upd.effective_chat.send_message.assert_called()
    text = upd.effective_chat.send_message.call_args[0][0]
    assert "done" in text.lower()


# =============================================================================
#  cmd_deletetask
# =============================================================================

@pytest.mark.asyncio
async def test_cmd_deletetask_no_args():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await cmd_deletetask(upd, ctx)
    upd.effective_chat.send_message.assert_called()


@pytest.mark.asyncio
async def test_cmd_deletetask_invalid_id():
    upd = _make_update(user_id=1111)
    ctx = _make_context(args=["xyz"])
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await cmd_deletetask(upd, ctx)
    upd.effective_chat.send_message.assert_called()


@pytest.mark.asyncio
async def test_cmd_deletetask_task_not_found():
    upd = _make_update(user_id=1111)
    ctx = _make_context(args=["99"])
    with patch("asyncio.sleep", new_callable=AsyncMock), \
         patch("app.bot.handlers.db.get_task", return_value=None):
        await cmd_deletetask(upd, ctx)
    upd.effective_chat.send_message.assert_called()


@pytest.mark.asyncio
async def test_cmd_deletetask_shows_confirm():
    upd = _make_update(user_id=1111)
    ctx = _make_context(args=["1"])
    with patch("app.bot.handlers.db.get_task", return_value=_TASK):
        await cmd_deletetask(upd, ctx)
    upd.effective_chat.send_message.assert_called()
    text = upd.effective_chat.send_message.call_args[0][0]
    assert "Delete" in text or "delete" in text.lower()


# =============================================================================
#  cmd_stats
# =============================================================================

@pytest.mark.asyncio
async def test_cmd_stats_sends_stats():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    with patch("app.bot.handlers.db.get_user", return_value=_USER_ROW), \
         patch("app.bot.handlers.db.get_user_stats", return_value=_STATS), \
         patch("app.bot.handlers.ai.generate_daily_motivation", return_value="Great job!"):
        await cmd_stats(upd, ctx)
    assert upd.effective_chat.send_message.call_count >= 2


@pytest.mark.asyncio
async def test_cmd_stats_user_none():
    upd = _make_update(user_id=1111)
    ctx = _make_context()
    with patch("app.bot.handlers.db.get_user", return_value=None), \
         patch("app.bot.handlers.db.get_user_stats", return_value=_STATS), \
         patch("app.bot.handlers.ai.generate_daily_motivation", return_value="Go!"):
        await cmd_stats(upd, ctx)
    upd.effective_chat.send_message.assert_called()


# =============================================================================
#  cmd_settimezone
# =============================================================================

@pytest.mark.asyncio
async def test_cmd_settimezone_sends_keyboard():
    upd = _make_update()
    ctx = _make_context()
    await cmd_settimezone(upd, ctx)
    upd.effective_chat.send_message.assert_called_once()


# =============================================================================
#  callback_main_menu
# =============================================================================

@pytest.mark.asyncio
async def test_callback_main_menu_answers_and_sends():
    upd = _make_cb_update(data="menu_main")
    ctx = _make_context()
    await callback_main_menu(upd, ctx)
    upd.callback_query.answer.assert_called_once()
    upd.callback_query.message.chat.send_message.assert_called_once()


# =============================================================================
#  unknown_command
# =============================================================================

@pytest.mark.asyncio
async def test_unknown_command_deletes_message():
    upd = _make_update()
    ctx = _make_context()
    await unknown_command(upd, ctx)
    upd.message.delete.assert_called_once()
