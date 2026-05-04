"""Tests for app/bot/keyboards.py"""

import pytest
from telegram import InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.bot.keyboards import (
    main_menu_keyboard,
    back_keyboard,
    filters_keyboard,
    timezone_keyboard,
    task_action_keyboard,
    delete_confirm_keyboard,
    task_list_keyboard,
    _edit_field_keyboard,
)


def _labels(kb: ReplyKeyboardMarkup) -> list[str]:
    return [btn.text for row in kb.keyboard for btn in row]


class TestMainMenuKeyboard:
    def test_returns_reply_keyboard(self):
        assert isinstance(main_menu_keyboard(), ReplyKeyboardMarkup)

    def test_resize_keyboard(self):
        assert main_menu_keyboard().resize_keyboard is True

    def test_has_add_task_button(self):
        assert "➕ Add Task" in _labels(main_menu_keyboard())

    def test_has_ai_button(self):
        assert "🤖 Add with AI" in _labels(main_menu_keyboard())

    def test_has_my_tasks_button(self):
        assert "📋 My Tasks" in _labels(main_menu_keyboard())

    def test_has_stats_button(self):
        assert "📊 Stats" in _labels(main_menu_keyboard())

    def test_has_filters_button(self):
        assert "🔍 Filters" in _labels(main_menu_keyboard())

    def test_has_timezone_button(self):
        assert "⚙️ Timezone" in _labels(main_menu_keyboard())

    def test_exactly_six_buttons(self):
        labels = _labels(main_menu_keyboard())
        assert len(labels) == 6


class TestBackKeyboard:
    def test_returns_reply_keyboard(self):
        assert isinstance(back_keyboard(), ReplyKeyboardMarkup)

    def test_has_back_button(self):
        assert "◀️ Back to Menu" in _labels(back_keyboard())

    def test_exactly_one_button(self):
        assert len(_labels(back_keyboard())) == 1


class TestFiltersKeyboard:
    def test_returns_reply_keyboard(self):
        assert isinstance(filters_keyboard(), ReplyKeyboardMarkup)

    def test_has_pending_filter(self):
        assert "⏳ Pending" in _labels(filters_keyboard())

    def test_has_done_filter(self):
        assert "✅ Done" in _labels(filters_keyboard())

    def test_has_in_progress_filter(self):
        assert "🔄 In Progress" in _labels(filters_keyboard())

    def test_has_work_category(self):
        assert "💼 Work" in _labels(filters_keyboard())

    def test_has_study_category(self):
        assert "📚 Study" in _labels(filters_keyboard())

    def test_has_personal_category(self):
        assert "🏠 Personal" in _labels(filters_keyboard())

    def test_has_health_category(self):
        assert "❤️ Health" in _labels(filters_keyboard())

    def test_has_finance_category(self):
        assert "💰 Finance" in _labels(filters_keyboard())

    def test_has_back_button(self):
        assert "◀️ Back to Menu" in _labels(filters_keyboard())


class TestTimezoneKeyboard:
    def test_returns_reply_keyboard(self):
        assert isinstance(timezone_keyboard(), ReplyKeyboardMarkup)

    def test_has_back_button(self):
        assert "◀️ Back to Menu" in _labels(timezone_keyboard())

    def test_timezone_buttons_start_with_globe(self):
        for label in _labels(timezone_keyboard()):
            if label != "◀️ Back to Menu":
                assert label.startswith("🌍"), f"Expected globe prefix on: {label}"

    def test_has_tashkent(self):
        assert any("Tashkent" in l for l in _labels(timezone_keyboard()))

    def test_has_utc(self):
        assert any("UTC" in l for l in _labels(timezone_keyboard()))

    def test_has_london(self):
        assert any("London" in l for l in _labels(timezone_keyboard()))

    def test_rows_have_at_most_two_buttons(self):
        kb = timezone_keyboard()
        for row in kb.keyboard:
            assert len(row) <= 2


class TestTaskActionKeyboard:
    def test_returns_reply_keyboard(self):
        assert isinstance(task_action_keyboard(1), ReplyKeyboardMarkup)

    def test_has_done_button(self):
        assert "✅ Done" in _labels(task_action_keyboard(1))

    def test_has_edit_button(self):
        assert "✏️ Edit" in _labels(task_action_keyboard(1))

    def test_has_delete_button(self):
        assert "🗑️ Delete" in _labels(task_action_keyboard(1))

    def test_has_back_button(self):
        assert "◀️ Back to Menu" in _labels(task_action_keyboard(1))

    def test_accepts_any_task_id(self):
        kb = task_action_keyboard(99999)
        assert isinstance(kb, ReplyKeyboardMarkup)


class TestDeleteConfirmKeyboard:
    def test_returns_reply_keyboard(self):
        assert isinstance(delete_confirm_keyboard(1), ReplyKeyboardMarkup)

    def test_has_confirm_button(self):
        assert "🗑️ Yes, Delete" in _labels(delete_confirm_keyboard(1))

    def test_has_cancel_button(self):
        assert "↩️ Cancel" in _labels(delete_confirm_keyboard(1))

    def test_exactly_two_buttons(self):
        assert len(_labels(delete_confirm_keyboard(1))) == 2


class TestTaskListKeyboard:
    def test_returns_inline_keyboard(self):
        tasks = [{"id": 1, "title": "Test task", "priority": "high", "status": "pending"}]
        assert isinstance(task_list_keyboard(tasks), InlineKeyboardMarkup)

    def test_empty_list_returns_empty_inline(self):
        kb = task_list_keyboard([])
        assert isinstance(kb, InlineKeyboardMarkup)
        assert len(kb.inline_keyboard) == 0

    def test_callback_data_format(self):
        tasks = [{"id": 7, "title": "My task", "priority": "medium", "status": "done"}]
        kb = task_list_keyboard(tasks)
        assert kb.inline_keyboard[0][0].callback_data == "task_view_7"

    def test_title_truncated_at_30_chars(self):
        long_title = "A" * 50
        tasks = [{"id": 1, "title": long_title, "priority": "low", "status": "pending"}]
        kb = task_list_keyboard(tasks)
        label = kb.inline_keyboard[0][0].text
        assert "A" * 31 not in label

    def test_multiple_tasks_multiple_rows(self):
        tasks = [
            {"id": 1, "title": "Task 1", "priority": "high", "status": "pending"},
            {"id": 2, "title": "Task 2", "priority": "low", "status": "done"},
            {"id": 3, "title": "Task 3", "priority": "medium", "status": "in_progress"},
        ]
        kb = task_list_keyboard(tasks)
        assert len(kb.inline_keyboard) == 3

    def test_unknown_priority_uses_fallback(self):
        tasks = [{"id": 1, "title": "Task", "priority": "nonexistent", "status": "pending"}]
        kb = task_list_keyboard(tasks)
        assert len(kb.inline_keyboard) == 1

    def test_each_task_has_one_button_per_row(self):
        tasks = [{"id": i, "title": f"Task {i}", "priority": "medium", "status": "pending"} for i in range(5)]
        kb = task_list_keyboard(tasks)
        for row in kb.inline_keyboard:
            assert len(row) == 1


class TestEditFieldKeyboard:
    def test_returns_reply_keyboard(self):
        assert isinstance(_edit_field_keyboard(), ReplyKeyboardMarkup)

    def test_has_title_field(self):
        assert "Title" in _labels(_edit_field_keyboard())

    def test_has_description_field(self):
        assert "Description" in _labels(_edit_field_keyboard())

    def test_has_category_field(self):
        assert "Category" in _labels(_edit_field_keyboard())

    def test_has_priority_field(self):
        assert "Priority" in _labels(_edit_field_keyboard())

    def test_has_deadline_field(self):
        assert "Deadline" in _labels(_edit_field_keyboard())

    def test_has_status_field(self):
        assert "Status" in _labels(_edit_field_keyboard())

    def test_has_cancel_button(self):
        assert "◀️ Cancel" in _labels(_edit_field_keyboard())

    def test_six_fields_plus_cancel(self):
        labels = _labels(_edit_field_keyboard())
        assert len(labels) == 7

    def test_rows_have_at_most_two_buttons(self):
        kb = _edit_field_keyboard()
        for row in kb.keyboard:
            assert len(row) <= 2
