"""All Telegram bot message and callback handlers for task management conversations."""

import asyncio
import logging

import pytz

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)
from telegram.constants import ParseMode

import app.core.database as db
import app.services.ai_service as ai
from app.core.formatters import (
    format_task_card,
    format_stats,
    escape_md,
)
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

logger = logging.getLogger(__name__)


# =============================================================================
#  HELPERS — message lifecycle
# =============================================================================

async def _delete(message) -> None:
    """Silently delete a message (ignores errors if already deleted)."""
    if message is None:
        return
    try:
        await message.delete()
    except Exception:
        pass


async def _safe_edit(message, text: str, reply_markup=None, parse_mode=ParseMode.MARKDOWN_V2):
    """Edit a message; silently ignore 'not modified' and 48-hour edit window expiry."""
    try:
        await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except BadRequest as e:
        err_msg = str(e).lower()
        if "message is not modified" in err_msg:
            return
        if "message can not be edited" in err_msg or "message can't be edited" in err_msg:
            return
        raise


# =============================================================================
#  CONVERSATION STATES
# =============================================================================

(AT_TITLE, AT_DESCRIPTION, AT_CATEGORY, AT_PRIORITY, AT_DEADLINE) = range(5)
(AI_INPUT,) = range(5, 6)
(EDIT_FIELD, EDIT_VALUE) = range(7, 9)

EDIT_FIELDS = ["Title", "Description", "Category", "Priority", "Deadline", "Status"]


# =============================================================================
#  TIMEZONE / FILTER MAPS  (single source of truth in this module)
# =============================================================================

_TIMEZONE_MAP = {
    "🌍 Tashkent":    "Asia/Tashkent",
    "🌍 Almaty":      "Asia/Almaty",
    "🌍 Dubai":       "Asia/Dubai",
    "🌍 Moscow":      "Europe/Moscow",
    "🌍 London":      "Europe/London",
    "🌍 Berlin":      "Europe/Berlin",
    "🌍 New York":    "America/New_York",
    "🌍 Los Angeles": "America/Los_Angeles",
    "🌍 Tokyo":       "Asia/Tokyo",
    "🌍 Sydney":      "Australia/Sydney",
    "🌍 UTC":         "UTC",
}

_FILTER_MAP = {
    "⏳ Pending":     ("status",   "pending"),
    "✅ Done":        ("status",   "done"),
    "🔄 In Progress": ("status",   "in_progress"),
    "💼 Work":        ("category", "work"),
    "📚 Study":       ("category", "study"),
    "🏠 Personal":    ("category", "personal"),
    "❤️ Health":      ("category", "health"),
    "💰 Finance":     ("category", "finance"),
}


# =============================================================================
#  /start  and  /help
# =============================================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.upsert_user(user.id, user.username or "", user.full_name or user.first_name or "User")
    logger.info(f"User @{user.username} (ID: {user.id}) started the bot")
    await update.message.reply_text(
        "🤖 *What Can This Bot Do?*\n\n"
        "Your personal *AI\\-powered Task Manager* inside Telegram\\.\n\n"
        "✅ Create \\& manage tasks manually or via AI\n"
        "🤖 AI detects priority, category and deadlines automatically\n"
        "🏷️ Organise by category: Work, Study, Personal, Health, Finance\n"
        "⏰ Reminders 30 min before every deadline\n"
        "📊 Productivity stats with AI coaching\n"
        "☀️ Daily morning digest\n\n",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=main_menu_keyboard(),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Help*\n\n"
        "➕ *Add Task* — step\\-by\\-step wizard\n"
        "🤖 *Add with AI* — describe in plain English\n"
        "📋 *My Tasks* — view all tasks \\(tap to open\\)\n"
        "📊 *Stats* — productivity dashboard\n"
        "🔍 *Filters* — filter by status or category\n"
        "⚙️ *Timezone* — set your local timezone\n\n"
        "💡 _Every task card has Done / Edit / Delete buttons_",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=main_menu_keyboard(),
    )


# =============================================================================
#  MAIN MENU HANDLERS  (reply keyboard buttons)
# =============================================================================

async def msg_handle_menu_mytasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle '📋 My Tasks' button."""
    await _delete(update.message)
    msg = await update.effective_chat.send_message(
        "📋 _Loading your tasks\\.\\.\\._",
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    context.user_data["menu_msg"] = msg
    await _render_task_list(msg, update.effective_user.id)


async def msg_handle_menu_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle '📊 Stats' button."""
    await _delete(update.message)
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    stats = await db.get_user_stats(user_id)
    name = user["full_name"] if user else "User"
    placeholder = await update.effective_chat.send_message(
        "📊 _Generating stats\\.\\.\\._",
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    motivation = await ai.generate_daily_motivation(stats)
    await _delete(placeholder)
    await update.effective_chat.send_message(
        f"{format_stats(stats, name)}\n\n💬 _{escape_md(motivation)}_",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=back_keyboard(),
    )


async def msg_handle_menu_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle '🔍 Filters' button."""
    await _delete(update.message)
    context.user_data.pop("current_task_id", None)
    context.user_data.pop("active_msg", None)
    msg = await update.effective_chat.send_message(
        "🔍 *Filter Tasks* — choose a filter:",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=filters_keyboard(),
    )
    context.user_data["menu_msg"] = msg


async def msg_handle_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle filter button presses."""
    button_text = update.message.text
    await _delete(update.message)

    filter_info = _FILTER_MAP.get(button_text)
    if not filter_info:
        return

    filter_type, filter_value = filter_info
    user_id = update.effective_user.id
    msg = await update.effective_chat.send_message(
        "📋 _Loading tasks\\.\\.\\._",
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    context.user_data["menu_msg"] = msg

    if filter_type == "status":
        await _render_task_list(msg, user_id, status=filter_value)
    else:
        await _render_task_list(msg, user_id, category=filter_value)


async def msg_handle_menu_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle '⚙️ Timezone' button."""
    await _delete(update.message)
    msg = await update.effective_chat.send_message(
        "⚙️ *Set Timezone* — tap your timezone:",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=timezone_keyboard(),
    )
    context.user_data["menu_msg"] = msg


async def msg_handle_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle timezone button presses."""
    button_text = update.message.text
    await _delete(update.message)

    tz_name = _TIMEZONE_MAP.get(button_text)
    if not tz_name:
        msg = await update.effective_chat.send_message(
            "⚠️ Invalid timezone selection\\.\n\nTry again:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=timezone_keyboard(),
        )
        context.user_data["menu_msg"] = msg
        return

    user_id = update.effective_user.id
    try:
        pytz.timezone(tz_name)
        await db.update_user_preferences(user_id, timezone=tz_name)
        logger.info(f"Timezone set: user={user_id} tz={tz_name}")
        msg = await update.effective_chat.send_message(
            f"✅ Timezone set to *{escape_md(tz_name)}*\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=main_menu_keyboard(),
        )
    except Exception as e:
        logger.warning(f"Invalid tz={tz_name} user={user_id}: {e}")
        msg = await update.effective_chat.send_message(
            f"⚠️ Could not set timezone `{escape_md(tz_name)}`\\.\n\nTry again:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=timezone_keyboard(),
        )
    context.user_data["menu_msg"] = msg


async def msg_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle '◀️ Back to Menu' button."""
    await _delete(update.message)
    active_msg = context.user_data.pop("active_msg", None)
    await _delete(active_msg)
    await update.effective_chat.send_message(
        "🏠", parse_mode=ParseMode.MARKDOWN_V2, 
        reply_markup= main_menu_keyboard()
    )


# =============================================================================
#  TASK LIST RENDERER  (shared)
# =============================================================================

async def _render_task_list(message, user_id: int, status=None, category=None):
    """Edit the message to show the task list inline keyboard."""
    tasks = await db.get_user_tasks(user_id, status=status, category=category)
    if not tasks:
        await _delete(message)
        await message.chat.send_message(
            "✅ *No tasks found* — you're all clear\\!",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=main_menu_keyboard(),
        )
        return

    label = ""
    if status:
        label = f" — {status.replace('_', ' ').capitalize()}"
    elif category:
        label = f" — {category.capitalize()}"

    await _safe_edit(
        message,
        f"📋 *Your Tasks{escape_md(label)}* \\({len(tasks)} total\\)\n\n"
        "_Tap any task to view full details:_",
        reply_markup=task_list_keyboard(tasks),
    )


# =============================================================================
#  /mytasks  and  /mytask <id>
# =============================================================================

async def cmd_mytasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status_map = {
        "pending": "pending", "done": "done",
        "in_progress": "in_progress", "progress": "in_progress",
    }
    category_map = {
        "work": "work", "study": "study", "personal": "personal",
        "health": "health", "finance": "finance", "general": "general",
    }
    status = category = None
    if context.args:
        arg = context.args[0].lower()
        if arg in status_map:
            status = status_map[arg]
        elif arg in category_map:
            category = category_map[arg]

    tasks = await db.get_user_tasks(user_id, status=status, category=category)
    label = ""
    if status:
        label = f" — {status.replace('_', ' ').capitalize()}"
    elif category:
        label = f" — {category.capitalize()}"

    if not tasks:
        await update.message.reply_text(
            "✅ *No tasks found* — you're all clear\\!",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=back_keyboard(),
        )
    else:
        await update.message.reply_text(
            f"📋 *Your Tasks{escape_md(label)}* \\({len(tasks)} total\\)\n\n"
            "_Tap any task to view full details:_",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=task_list_keyboard(tasks),
        )
    await _delete(update.message)


async def cmd_mytask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /mytask \\<id\\>", parse_mode=ParseMode.MARKDOWN_V2)
        await _delete(update.message)
        return
    try:
        task_id = int(context.args[0])
    except ValueError:
        await _delete(update.message)
        return

    task = await db.get_task(task_id, user_id)
    if not task:
        await update.message.reply_text(
            f"⚠️ Task `\\#{task_id}` not found\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=back_keyboard(),
        )
        await _delete(update.message)
        return

    user = await db.get_user(user_id)
    user_tz = user["timezone"] if user else "UTC"
    msg = await update.message.reply_text(
        format_task_card(task, user_tz=user_tz),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=task_action_keyboard(task_id),
    )
    context.user_data["current_task_id"] = task_id
    context.user_data["active_msg"] = msg
    await _delete(update.message)


# =============================================================================
#  TASK LIST INLINE CALLBACKS
# =============================================================================

async def callback_task_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View task details — called from task list inline buttons."""
    query = update.callback_query
    user_id = query.from_user.id
    try:
        task_id = int(query.data.split("_")[-1])
    except ValueError:
        await query.answer("Invalid request.", show_alert=True)
        return

    task = await db.get_task(task_id, user_id)
    if not task:
        await query.answer("Task not found.", show_alert=True)
        return

    user = await db.get_user(user_id)
    user_tz = user["timezone"] if user else "UTC"
    await query.answer()
    context.user_data["current_task_id"] = task_id
    await _delete(query.message)
    msg = await query.message.chat.send_message(
        format_task_card(task, user_tz=user_tz),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=task_action_keyboard(task_id),
    )
    context.user_data["active_msg"] = msg


# =============================================================================
#  TASK ACTION HANDLERS  (reply keyboard: Done / Edit / Delete)
# =============================================================================

async def msg_handle_task_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle '✅ Done' task-action button."""
    task_id = context.user_data.get("current_task_id")
    if task_id is None:
        # No active task — treat as a filter shortcut
        return await msg_handle_filter(update, context)

    await _delete(update.message)
    user_id = update.effective_user.id
    active_msg = context.user_data.pop("active_msg", None)

    task = await db.get_task(task_id, user_id)
    if not task:
        await _delete(active_msg)
        await update.effective_chat.send_message(
            f"⚠️ Task `\\#{task_id}` not found\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=back_keyboard(),
        )
        context.user_data.pop("current_task_id", None)
        return

    if task["status"] == "done":
        await update.effective_chat.send_message(
            "ℹ️ Task is already marked as done\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=task_action_keyboard(task_id),
        )
        return

    await db.update_task(task_id, user_id, status="done")
    task = await db.get_task(task_id, user_id)
    logger.info(f"Task done: ID={task_id} user={user_id}")

    user = await db.get_user(user_id)
    user_tz = user["timezone"] if user else "UTC"
    await _delete(active_msg)
    msg = await update.effective_chat.send_message(
        f"🎉 *Done\\!*\n\n{format_task_card(task, user_tz=user_tz)}",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=task_action_keyboard(task_id),
    )
    context.user_data["current_task_id"] = task_id
    context.user_data["active_msg"] = msg


async def msg_handle_task_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle '✏️ Edit' task-action button — entry point for edit conversation."""
    await _delete(update.message)
    user_id = update.effective_user.id
    task_id = context.user_data.get("current_task_id")
    active_msg = context.user_data.pop("active_msg", None)

    if task_id is None:
        await update.effective_chat.send_message(
            "⚠️ No task selected\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    task = await db.get_task(task_id, user_id)
    if not task:
        await _delete(active_msg)
        await update.effective_chat.send_message(
            f"⚠️ Task `\\#{task_id}` not found\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=back_keyboard(),
        )
        return ConversationHandler.END

    await _delete(active_msg)
    context.user_data["edit_id"] = task_id
    context.user_data["edit_user_id"] = user_id
    msg = await update.effective_chat.send_message(
        f"✏️ *Edit Task \\#{task_id}*\n\nWhich field would you like to edit?",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_edit_field_keyboard(),
    )
    context.user_data["edit_orig_msg"] = msg
    return EDIT_FIELD


async def msg_handle_task_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle '🗑️ Delete' task-action button."""
    await _delete(update.message)
    user_id = update.effective_user.id
    task_id = context.user_data.get("current_task_id")
    active_msg = context.user_data.pop("active_msg", None)

    if task_id is None:
        await update.effective_chat.send_message(
            "⚠️ No task selected\\.", parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    task = await db.get_task(task_id, user_id)
    if not task:
        await _delete(active_msg)
        await update.effective_chat.send_message(
            f"⚠️ Task `\\#{task_id}` not found\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=back_keyboard(),
        )
        return

    await _delete(active_msg)
    context.user_data["delete_task_id"] = task_id
    msg = await update.effective_chat.send_message(
        f"⚠️ Delete task `\\#{task_id}`?\n\n*{escape_md(task['title'])}*",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=delete_confirm_keyboard(task_id),
    )
    context.user_data["delete_msg"] = msg


async def msg_handle_task_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle '🗑️ Yes, Delete' confirmation button."""
    await _delete(update.message)
    user_id = update.effective_user.id
    task_id = context.user_data.get("delete_task_id")
    delete_msg = context.user_data.pop("delete_msg", None)

    if task_id is None:
        await update.effective_chat.send_message(
            "⚠️ No task selected\\.", parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    await _delete(delete_msg)
    deleted = await db.delete_task(task_id, user_id)
    if deleted:
        logger.info(f"Task deleted: ID={task_id} user={user_id}")
        await update.effective_chat.send_message(
            f"🗑️ Task `\\#{task_id}` deleted\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=main_menu_keyboard(),
        )
    else:
        await update.effective_chat.send_message(
            "⚠️ Could not delete task\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=back_keyboard(),
        )
    context.user_data.pop("current_task_id", None)
    context.user_data.pop("delete_task_id", None)


async def msg_handle_task_delete_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle '↩️ Cancel' deletion button — restore task card."""
    await _delete(update.message)
    user_id = update.effective_user.id
    task_id = context.user_data.get("delete_task_id", context.user_data.get("current_task_id"))
    delete_msg = context.user_data.pop("delete_msg", None)

    await _delete(delete_msg)

    if task_id is None:
        await update.effective_chat.send_message(
            "🏠", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=main_menu_keyboard()
        )
        return

    task = await db.get_task(task_id, user_id)
    if not task:
        await update.effective_chat.send_message(
            f"⚠️ Task `\\#{task_id}` not found\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=back_keyboard(),
        )
        return

    user = await db.get_user(user_id)
    user_tz = user["timezone"] if user else "UTC"
    msg = await update.effective_chat.send_message(
        format_task_card(task, user_tz=user_tz),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=task_action_keyboard(task_id),
    )
    context.user_data["current_task_id"] = task_id
    context.user_data["active_msg"] = msg
    context.user_data.pop("delete_task_id", None)


# =============================================================================
#  COMMAND ALIASES  (/done /deletetask /stats /settimezone)
# =============================================================================

async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await _delete(update.message)
    if not context.args:
        m = await update.effective_chat.send_message(
            "⚠️ Usage: /done \\<task_id\\>", parse_mode=ParseMode.MARKDOWN_V2
        )
        await asyncio.sleep(3)
        await _delete(m)
        return
    try:
        task_id = int(context.args[0])
    except ValueError:
        m = await update.effective_chat.send_message(
            r"⚠️ Invalid task ID\.", parse_mode=ParseMode.MARKDOWN_V2
        )
        await asyncio.sleep(3)
        await _delete(m)
        return

    task = await db.get_task(task_id, user_id)
    if not task:
        m = await update.effective_chat.send_message(
            rf"⚠️ Task `\#{task_id}` not found\.", parse_mode=ParseMode.MARKDOWN_V2
        )
        await asyncio.sleep(3)
        await _delete(m)
        return

    if task["status"] == "done":
        m = await update.effective_chat.send_message(
            rf"ℹ️ Task `\#{task_id}` is already marked as done\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=back_keyboard(),
        )
        await asyncio.sleep(3)
        await _delete(m)
        return

    await db.update_task(task_id, user_id, status="done")
    task = await db.get_task(task_id, user_id)
    await update.effective_chat.send_message(
        f"✅ Task `\\#{task_id}` *{escape_md(task['title'])}* marked as done\\! 🎉",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=back_keyboard(),
    )


async def cmd_deletetask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await _delete(update.message)
    if not context.args:
        m = await update.effective_chat.send_message(
            "⚠️ Usage: /deletetask \\<task_id\\>", parse_mode=ParseMode.MARKDOWN_V2
        )
        await asyncio.sleep(3)
        await _delete(m)
        return
    try:
        task_id = int(context.args[0])
    except ValueError:
        m = await update.effective_chat.send_message(
            r"⚠️ Invalid task ID\.", parse_mode=ParseMode.MARKDOWN_V2
        )
        await asyncio.sleep(3)
        await _delete(m)
        return

    task = await db.get_task(task_id, user_id)
    if not task:
        m = await update.effective_chat.send_message(
            rf"⚠️ Task `\#{task_id}` not found\.", parse_mode=ParseMode.MARKDOWN_V2
        )
        await asyncio.sleep(3)
        await _delete(m)
        return

    context.user_data["delete_task_id"] = task_id
    msg = await update.effective_chat.send_message(
        f"⚠️ Delete task `\\#{task_id}`?\n\n*{escape_md(task['title'])}*",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=delete_confirm_keyboard(task_id),
    )
    context.user_data["delete_msg"] = msg


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await _delete(update.message)
    user = await db.get_user(user_id)
    stats = await db.get_user_stats(user_id)
    name = user["full_name"] if user else "User"
    placeholder = await update.effective_chat.send_message(
        "📊 _Generating stats\\.\\.\\._", parse_mode=ParseMode.MARKDOWN_V2
    )
    motivation = await ai.generate_daily_motivation(stats)
    await _delete(placeholder)
    await update.effective_chat.send_message(
        f"{format_stats(stats, name)}\n\n💬 _{escape_md(motivation)}_",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=back_keyboard(),
    )


async def cmd_settimezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _delete(update.message)
    await update.effective_chat.send_message(
        "⚙️ *Set Timezone* — tap your timezone:",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=timezone_keyboard(),
    )


# =============================================================================
#  INLINE CALLBACKS  (task list / main menu)
# =============================================================================

async def callback_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Back to Menu' inline button from the task list."""
    query = update.callback_query
    await query.answer()
    await _delete(query.message)
    await query.message.chat.send_message(
        "🏠", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=main_menu_keyboard()
    )


# =============================================================================
#  FALLBACK
# =============================================================================

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _delete(update.message)