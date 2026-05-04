"""Keyboard builders for all Telegram bot interactions."""

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)

from app.core.formatters import PRIORITY_EMOJI, STATUS_EMOJI


# =============================================================================
#  Main navigation
# =============================================================================

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["➕ Add Task", "🤖 Add with AI"],
            ["📋 My Tasks", "📊 Stats"],
            ["🔍 Filters",  "⚙️ Timezone"],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["◀️ Back to Menu"]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


# =============================================================================
#  Filters and timezone
# =============================================================================

def filters_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["⏳ Pending", "✅ Done", "🔄 In Progress"],
            ["💼 Work", "📚 Study", "🏠 Personal"],
            ["❤️ Health", "💰 Finance"],
            ["◀️ Back to Menu"],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def timezone_keyboard() -> ReplyKeyboardMarkup:
    zones = [
        "🌍 Tashkent", "🌍 Almaty", "🌍 Dubai",    "🌍 Moscow",
        "🌍 London",   "🌍 Berlin", "🌍 New York",  "🌍 Los Angeles",
        "🌍 Tokyo",    "🌍 Sydney", "🌍 UTC",
    ]
    rows = [zones[i:i + 2] for i in range(0, len(zones), 2)]
    rows.append(["◀️ Back to Menu"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


# =============================================================================
#  Task action keyboard  (Done / Edit / Delete)
# =============================================================================

def task_action_keyboard(task_id: int) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["✅ Done", "✏️ Edit", "🗑️ Delete"],
         ["◀️ Back to Menu"]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def delete_confirm_keyboard(task_id: int) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["🗑️ Yes, Delete", "↩️ Cancel"]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def task_list_keyboard(tasks: list) -> InlineKeyboardMarkup:
    """Task list as inline buttons for 'My Tasks' section."""
    rows = []
    for t in tasks:
        p = PRIORITY_EMOJI.get(t["priority"], "⚪")
        s = STATUS_EMOJI.get(t["status"], "❓")
        label = f"{s}{p} #{t['id']}  {t['title'][:30]}"
        rows.append([InlineKeyboardButton(label, callback_data=f"task_view_{t['id']}")])
    return InlineKeyboardMarkup(rows)


# =============================================================================
#  Edit field keyboard
# =============================================================================

def _edit_field_keyboard() -> ReplyKeyboardMarkup:
    fields = ["Title", "Description", "Category", "Priority", "Deadline", "Status"]
    rows = [fields[i:i + 2] for i in range(0, len(fields), 2)]
    rows.append(["◀️ Cancel"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)