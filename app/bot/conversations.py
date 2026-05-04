"""Conversation handlers for the task-creation and edit wizards."""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.constants import ParseMode

import app.core.database as db
import app.services.ai_service as ai
from app.core.formatters import format_task_card, escape_md
from app.bot.keyboards import task_action_keyboard, _edit_field_keyboard, main_menu_keyboard, back_keyboard

# One-way import — conversations depends on handlers, never the reverse.
from app.bot.handlers import (
    _safe_edit,
    _delete,
    AT_TITLE, AT_DESCRIPTION, AT_CATEGORY, AT_PRIORITY, AT_DEADLINE,
    AI_INPUT,
    EDIT_FIELD, EDIT_VALUE, EDIT_FIELDS,
    msg_handle_task_edit,
)

logger = logging.getLogger(__name__)


# =============================================================================
#  STEP KEYBOARDS  (wizard-only; local definitions take precedence over imports)
# =============================================================================

def _category_inline(step: str = "3/5") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💼 Work",      callback_data="wz_cat_work"),
         InlineKeyboardButton("📚 Study",     callback_data="wz_cat_study")],
        [InlineKeyboardButton("🏠 Personal",  callback_data="wz_cat_personal"),
         InlineKeyboardButton("❤️ Health",    callback_data="wz_cat_health")],
        [InlineKeyboardButton("💰 Finance",   callback_data="wz_cat_finance"),
         InlineKeyboardButton("📋 General",   callback_data="wz_cat_general")],
    ])


def _priority_inline(step: str = "4/5") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔴 High",   callback_data="wz_pri_high"),
        InlineKeyboardButton("🟡 Medium", callback_data="wz_pri_medium"),
        InlineKeyboardButton("🟢 Low",    callback_data="wz_pri_low"),
    ]])


def _skip_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏭ Skip", callback_data="wz_skip"),
    ]])



# =============================================================================
#  DEADLINE PARSER
# =============================================================================

def parse_deadline(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (iso_string, None) on success, (None, error_hint) on failure.
    Accepts natural language and many date formats.
    """
    text = text.strip().lower()
    now  = datetime.utcnow()

    if text == "today":
        return now.replace(hour=9, minute=0, second=0, microsecond=0).isoformat(), None
    if text == "tomorrow":
        return (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat(), None
    if text == "next week":
        return (now + timedelta(weeks=1)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat(), None

    m = re.match(r"in\s+(\d+)\s+(hour|hours|day|days|week|weeks)", text)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        if "hour" in unit:
            return (now + timedelta(hours=n)).replace(second=0, microsecond=0).isoformat(), None
        if "day" in unit:
            return (now + timedelta(days=n)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat(), None
        if "week" in unit:
            return (now + timedelta(weeks=n)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat(), None

    weekdays = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    for i, day in enumerate(weekdays):
        if text.startswith(f"next {day}") or text == day:
            days_ahead = (i - now.weekday() + 7) % 7 or 7
            return (now + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat(), None

    for fmt in [
        "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d",
        "%d/%m/%Y %H:%M", "%d/%m/%Y",
        "%d.%m.%Y %H:%M", "%d.%m.%Y",
        "%d-%m-%Y %H:%M", "%d-%m-%Y",
        "%m/%d/%Y %H:%M", "%m/%d/%Y",
    ]:
        try:
            dt = datetime.strptime(text.strip(), fmt)
            if "%H" not in fmt:
                dt = dt.replace(hour=9, minute=0, second=0)
            return dt.isoformat(), None
        except ValueError:
            continue

    return None, (
        "I couldn't understand that date\\. Try:\n"
        "`2026-03-15 14:30` \\| `tomorrow` \\| `in 3 days` \\| `next monday`"
    )


# =============================================================================
#  /addtask — step-by-step wizard
# =============================================================================

_CANCEL_KEYBOARD = ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True)


async def addtask_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry via /addtask command — send the first wizard message."""
    context.user_data.pop("new_task", None)
    msg = await update.message.reply_text(
        "📝 *New Task — Step 1/5*\n\nWhat is the task *title*?\n\n"
        "_Type your answer and send it\\._",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_CANCEL_KEYBOARD,
    )
    await _delete(update.message)
    context.user_data["wz_msg"] = msg
    return AT_TITLE


async def _wz_edit(context, text: str, reply_markup=None):
    """Update the wizard message: try edit first, fall back to delete + resend."""
    msg = context.user_data.get("wz_msg")
    if not msg:
        return
    try:
        await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
    except Exception:
        await _delete(msg)
        new_msg = await msg.chat.send_message(
            text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup
        )
        context.user_data["wz_msg"] = new_msg


async def addtask_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _delete(update.message)
    context.user_data["new_task"] = {"title": update.message.text.strip()}
    await _wz_edit(
        context,
        "📝 *New Task — Step 2/5*\n\n"
        f"*Title:* {escape_md(update.message.text.strip())}\n\n"
        "Add a *description* or skip:",
        reply_markup=_skip_inline(),
    )
    return AT_DESCRIPTION


async def addtask_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _delete(update.message)
    context.user_data["new_task"]["description"] = update.message.text.strip()
    task = context.user_data["new_task"]
    await _wz_edit(
        context,
        f"📝 *New Task — Step 3/5*\n\n"
        f"*Title:* {escape_md(task['title'])}\n\n"
        "Choose a *category:*",
        reply_markup=_category_inline(),
    )
    return AT_CATEGORY


async def addtask_skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the ⏭ Skip inline button for description."""
    query = update.callback_query
    await query.answer()
    context.user_data["new_task"]["description"] = ""
    task = context.user_data["new_task"]
    await _safe_edit(
        query.message,
        f"📝 *New Task — Step 3/5*\n\n"
        f"*Title:* {escape_md(task['title'])}\n\n"
        "Choose a *category:*",
        reply_markup=_category_inline(),
    )
    return AT_CATEGORY


async def addtask_category_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Category selected via inline button."""
    query = update.callback_query
    await query.answer()
    cat = query.data.replace("wz_cat_", "")
    context.user_data["new_task"]["category"] = cat
    task = context.user_data["new_task"]
    await _safe_edit(
        query.message,
        f"📝 *New Task — Step 4/5*\n\n"
        f"*Title:* {escape_md(task['title'])}\n"
        f"*Category:* {cat.capitalize()}\n\n"
        "Set *priority:*",
        reply_markup=_priority_inline(),
    )
    return AT_PRIORITY


async def addtask_priority_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Priority selected via inline button."""
    query = update.callback_query
    await query.answer()
    pri = query.data.replace("wz_pri_", "")
    context.user_data["new_task"]["priority"] = pri
    task = context.user_data["new_task"]
    await _safe_edit(
        query.message,
        f"📝 *New Task — Step 5/5*\n\n"
        f"*Title:* {escape_md(task['title'])}\n"
        f"*Category:* {task['category'].capitalize()}\n"
        f"*Priority:* {pri.capitalize()}\n\n"
        "Set a *deadline* or skip:\n"
        "`2026-03-15 14:30` \\| `tomorrow` \\| `in 3 days`",
        reply_markup=_skip_inline(),
    )
    return AT_DEADLINE


async def addtask_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deadline entered as text."""
    await _delete(update.message)
    text = update.message.text.strip()
    deadline, err = parse_deadline(text)
    if err:
        await _wz_edit(
            context,
            f"⚠️ {err}\n\nOr skip:",
            reply_markup=_skip_inline(),
        )
        return AT_DEADLINE

    return await _finish_addtask(update.callback_query if update.callback_query else None,
                                  context, deadline)


async def addtask_skip_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip deadline inline button."""
    query = update.callback_query
    await query.answer()
    return await _finish_addtask(query, context, deadline=None)


async def _finish_addtask(query, context, deadline):
    wz_msg    = context.user_data.get("wz_msg")
    user_id   = wz_msg.chat_id if wz_msg else None

    task_data           = context.user_data["new_task"]
    task_data["deadline"] = deadline

    task_id = await db.create_task(user_id=user_id, **task_data)
    task    = await db.get_task(task_id, user_id)
    logger.info(f"Task created: ID={task_id} user={user_id} title='{task_data['title']}'")

    user_row = await db.get_user(user_id)
    user_tz  = user_row["timezone"] if user_row else "UTC"
    await _delete(wz_msg)
    msg = await wz_msg.chat.send_message(
        f"✅ *Task created\\!*\n\n{format_task_card(task, user_tz=user_tz)}",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=task_action_keyboard(task_id),
    )
    context.user_data.pop("new_task", None)
    context.user_data.pop("wz_msg", None)
    context.user_data["active_msg"] = msg
    context.user_data["current_task_id"] = task_id
    return ConversationHandler.END


async def addtask_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_task", None)
    wz_msg = context.user_data.pop("wz_msg", None)
    if wz_msg:
        await _delete(wz_msg)
    if update.message:
        await _delete(update.message)
    await update.effective_chat.send_message(
        "❌ Cancelled\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


# =============================================================================
#  /addtask_ai — AI flow  (single-message)
# =============================================================================

async def addtask_ai_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "🤖 *AI Task Creation*\n\n"
        "Describe your task in plain English:\n"
        "• _'Submit the quarterly report by Friday, urgent'_\n"
        "• _'Buy groceries tomorrow at 5 PM'_\n\n"
        "_Type your description and send it\\._",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_CANCEL_KEYBOARD,
    )
    await _delete(update.message)
    context.user_data["wz_msg"] = msg
    return AI_INPUT


async def addtask_ai_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text    = update.message.text.strip()
    await _delete(update.message)

    wz_msg = context.user_data.get("wz_msg")
    await _safe_edit(wz_msg, "🔄 _Analyzing your task with AI\\.\\.\\._")

    user   = await db.get_user(user_id)
    tz     = user["timezone"] if user else "UTC"
    parsed = await ai.parse_task_from_text(text, tz)

    if not parsed:
        await _delete(wz_msg)
        await wz_msg.chat.send_message(
            "⚠️ Couldn't parse that task\\. Please try /addtask for manual entry\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=main_menu_keyboard(),
        )
        context.user_data.pop("wz_msg", None)
        return ConversationHandler.END

    task_id = await db.create_task(user_id=user_id, **parsed)
    task    = await db.get_task(task_id, user_id)
    logger.info(f"AI task created: ID={task_id} user={user_id}")

    await _delete(wz_msg)
    msg = await wz_msg.chat.send_message(
        f"✅ *AI created your task\\!*\n\n{format_task_card(task, user_tz=tz)}\n\n"
        "_AI auto\\-detected category, priority, and deadline\\._",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=task_action_keyboard(task_id),
    )
    context.user_data.pop("wz_msg", None)
    context.user_data["active_msg"] = msg
    context.user_data["current_task_id"] = task_id
    return ConversationHandler.END


async def addtask_ai_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wz_msg = context.user_data.pop("wz_msg", None)
    if wz_msg:
        await _delete(wz_msg)
    if update.message:
        await _delete(update.message)
    await update.effective_chat.send_message(
        "❌ Cancelled\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


# =============================================================================
#  /edittask — Edit conversation  (single-message, inline field selector)
# =============================================================================

def _edit_field_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline version of the field selector — used when editing from the task card inline button."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Title",       callback_data="ef_title"),
         InlineKeyboardButton("📄 Description", callback_data="ef_description")],
        [InlineKeyboardButton("🗂️ Category",   callback_data="ef_category"),
         InlineKeyboardButton("⚡ Priority",    callback_data="ef_priority")],
        [InlineKeyboardButton("📅 Deadline",   callback_data="ef_deadline"),
         InlineKeyboardButton("🔄 Status",     callback_data="ef_status")],
    ])


async def callback_task_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✏️ Edit button — show field selector inline."""
    query   = update.callback_query
    try:
        task_id = int(query.data.split("_")[-1])
    except ValueError:
        await query.answer("Invalid request.", show_alert=True)
        return ConversationHandler.END
    await query.answer()

    context.user_data["edit_id"]       = task_id
    context.user_data["edit_user_id"]  = update.effective_user.id
    context.user_data["edit_orig_msg"] = query.message

    await _safe_edit(
        query.message,
        f"✏️ *Editing task \\#{task_id}*\n\nWhich field do you want to change?",
        reply_markup=_edit_field_inline_keyboard(),
    )
    return EDIT_FIELD


async def callback_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User tapped a field button (ef_title, ef_priority, etc.)."""
    query = update.callback_query
    field = query.data.replace("ef_", "")
    await query.answer()
    context.user_data["edit_field"] = field

    prompts = {
        "title":       "Enter the new *title:*\n\n_Type and send it\\._",
        "description": "Enter the new *description* or skip:",
        "category":    "Choose a new *category:*",
        "priority":    "Choose a new *priority:*",
        "deadline":    "Enter new *deadline* or skip:\n`2026-03-15 14:30` \\| `tomorrow` \\| `in 3 days`",
        "status":      "Choose a new *status:*",
    }
    keyboards = {
        "category": _category_inline(),
        "priority": _priority_inline(),
        "description": _skip_inline(),
        "deadline": _skip_inline(),
        "status": InlineKeyboardMarkup([[
            InlineKeyboardButton("⏳ Pending",     callback_data="ef_val_pending"),
            InlineKeyboardButton("🔄 In Progress", callback_data="ef_val_in_progress"),
        ],[
            InlineKeyboardButton("✅ Done",        callback_data="ef_val_done"),
            InlineKeyboardButton("❌ Cancelled",   callback_data="ef_val_cancelled"),
        ]]),
    }

    await _safe_edit(
        query.message,
        f"✏️ *Editing task \\#{context.user_data['edit_id']} — {field.capitalize()}*\n\n{prompts.get(field, '')}",
        reply_markup=keyboards.get(field),
    )
    return EDIT_VALUE


async def callback_edit_value_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles inline button selections during edit (category, priority, status, skip)."""
    query = update.callback_query
    await query.answer()
    data  = query.data
    field = context.user_data.get("edit_field", "")

    # Skip
    if data == "wz_skip":
        value = None
    # Category
    elif data.startswith("wz_cat_"):
        value = data.replace("wz_cat_", "")
    # Priority
    elif data.startswith("wz_pri_"):
        value = data.replace("wz_pri_", "")
    # Status
    elif data.startswith("ef_val_"):
        value = data.replace("ef_val_", "")
    else:
        return EDIT_VALUE

    return await _apply_edit(query.message, context, value)


async def edittask_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles free-text input during edit (title, description, deadline)."""
    raw   = update.message.text.strip()
    field = context.user_data.get("edit_field", "")
    await _delete(update.message)

    if field == "deadline":
        value, err = parse_deadline(raw)
        if err:
            orig = context.user_data.get("edit_orig_msg")
            if orig:
                await _safe_edit(orig, f"⚠️ {err}\n\nOr skip:", reply_markup=_skip_inline())
            else:
                await update.effective_chat.send_message(
                    f"⚠️ {err}\n\nOr skip:",
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=_skip_inline(),
                )
            return EDIT_VALUE
    else:
        value = raw

    return await _apply_edit(context.user_data.get("edit_orig_msg"), context, value)


async def _apply_edit(message, context, value):
    """Write the edit to DB and refresh the task card in the original message."""
    user_id  = context.user_data.get("edit_user_id")
    task_id  = context.user_data["edit_id"]
    field    = context.user_data["edit_field"]

    updated  = await db.update_task(task_id, user_id, **{field: value})
    task     = await db.get_task(task_id, user_id)

    if updated and task:
        logger.info(f"Task edited: ID={task_id} user={user_id} field={field}")
        user_row = await db.get_user(user_id)
        user_tz  = user_row["timezone"] if user_row else "UTC"
        await _delete(message)
        msg = await message.chat.send_message(
            f"✅ *Updated\\!*\n\n{format_task_card(task, user_tz=user_tz)}",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=task_action_keyboard(task_id),
        )
        context.user_data["active_msg"] = msg
        context.user_data["current_task_id"] = task_id
    else:
        await _delete(message)
        await message.chat.send_message(
            "⚠️ Could not update task\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=main_menu_keyboard(),
        )

    context.user_data.pop("edit_id", None)
    context.user_data.pop("edit_field", None)
    context.user_data.pop("edit_orig_msg", None)
    return ConversationHandler.END


async def edittask_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry via /edittask <id> command."""
    args = context.args
    if args:
        try:
            task_id = int(args[0])
            user_id = update.effective_user.id
            task    = await db.get_task(task_id, user_id)
            if not task:
                m = await update.message.reply_text(f"⚠️ Task `\\#{task_id}` not found\\.", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=back_keyboard())
                await _delete(update.message)
                return ConversationHandler.END
            msg = await update.message.reply_text(
                f"✏️ *Editing task \\#{task_id}*\n\nWhich field do you want to change?",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=_edit_field_keyboard(),
            )
            await _delete(update.message)
            context.user_data["edit_id"]       = task_id
            context.user_data["edit_user_id"] = user_id
            context.user_data["edit_orig_msg"]  = msg
            return EDIT_FIELD
        except ValueError:
            pass

    m = await update.message.reply_text("Usage: /edittask \\<id\\>", parse_mode=ParseMode.MARKDOWN_V2)
    await _delete(update.message)
    return ConversationHandler.END


async def edittask_field_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User tapped a field name from the reply keyboard field selector."""
    field = update.message.text.strip().lower()
    await _delete(update.message)
    context.user_data["edit_field"] = field

    prompts = {
        "title":       "Enter the new *title:*\n\n_Type and send it\\._",
        "description": "Enter the new *description* or skip:",
        "category":    "Choose a new *category:*",
        "priority":    "Choose a new *priority:*",
        "deadline":    "Enter new *deadline* or skip:\n`2026-03-15 14:30` \\| `tomorrow` \\| `in 3 days`",
        "status":      "Choose a new *status:*",
    }
    keyboards = {
        "category":    _category_inline(),
        "priority":    _priority_inline(),
        "description": _skip_inline(),
        "deadline":    _skip_inline(),
        "status": InlineKeyboardMarkup([[
            InlineKeyboardButton("⏳ Pending",     callback_data="ef_val_pending"),
            InlineKeyboardButton("🔄 In Progress", callback_data="ef_val_in_progress"),
        ],[
            InlineKeyboardButton("✅ Done",        callback_data="ef_val_done"),
            InlineKeyboardButton("❌ Cancelled",   callback_data="ef_val_cancelled"),
        ]]),
    }
    task_id = context.user_data.get("edit_id", "?")
    orig    = context.user_data.get("edit_orig_msg")
    await _safe_edit(
        orig,
        f"✏️ *Editing task \\#{task_id} — {field.capitalize()}*\n\n{prompts.get(field, '')}",
        reply_markup=keyboards.get(field),
    )
    return EDIT_VALUE


async def edittask_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orig = context.user_data.pop("edit_orig_msg", None)
    context.user_data.pop("edit_id", None)
    context.user_data.pop("edit_user_id", None)
    context.user_data.pop("edit_field", None)
    if orig:
        await _delete(orig)
    if update.message:
        await _delete(update.message)
    await update.effective_chat.send_message(
        "❌ Cancelled\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


# =============================================================================
#  CONVERSATION HANDLER BUILDERS
# =============================================================================

_CANCEL_FILTER = filters.TEXT & filters.Regex(r"^❌ Cancel$")


def build_addtask_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("addtask", addtask_start),
            MessageHandler(filters.TEXT & filters.Regex(r"^➕ Add Task$"), addtask_start),
        ],
        states={
            AT_TITLE: [
                MessageHandler(_CANCEL_FILTER, addtask_cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, addtask_title),
            ],
            AT_DESCRIPTION: [
                MessageHandler(_CANCEL_FILTER, addtask_cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, addtask_description),
                CallbackQueryHandler(addtask_skip_description, pattern=r"^wz_skip$"),
            ],
            AT_CATEGORY: [
                CallbackQueryHandler(addtask_category_inline, pattern=r"^wz_cat_"),
            ],
            AT_PRIORITY: [
                CallbackQueryHandler(addtask_priority_inline, pattern=r"^wz_pri_"),
            ],
            AT_DEADLINE: [
                MessageHandler(_CANCEL_FILTER, addtask_cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, addtask_deadline),
                CallbackQueryHandler(addtask_skip_deadline, pattern=r"^wz_skip$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", addtask_cancel),
            MessageHandler(_CANCEL_FILTER, addtask_cancel),
        ],
        allow_reentry=True,
    )


def build_addtask_ai_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("addtask_ai", addtask_ai_start),
            MessageHandler(filters.TEXT & filters.Regex(r"^🤖 Add with AI$"), addtask_ai_start),
        ],
        states={
            AI_INPUT: [
                MessageHandler(_CANCEL_FILTER, addtask_ai_cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, addtask_ai_input),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", addtask_ai_cancel),
            MessageHandler(_CANCEL_FILTER, addtask_ai_cancel),
        ],
        allow_reentry=True,
    )


def build_edittask_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("edittask", edittask_start),
            MessageHandler(filters.TEXT & filters.Regex(r"^✏️ Edit$"), msg_handle_task_edit),
            CallbackQueryHandler(callback_task_edit, pattern=r"^task_edit_\d+$"),
        ],
        states={
            EDIT_FIELD: [
                CallbackQueryHandler(callback_edit_field, pattern=r"^ef_"),
                MessageHandler(
                    filters.TEXT & filters.Regex(r"^(Title|Description|Category|Priority|Deadline|Status)$"),
                    edittask_field_text,
                ),
            ],
            EDIT_VALUE: [
                MessageHandler(filters.TEXT & filters.Regex(r"^◀️ Cancel$"), edittask_cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edittask_value),
                CallbackQueryHandler(callback_edit_value_inline, pattern=r"^(wz_skip|wz_cat_|wz_pri_|ef_val_)"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", edittask_cancel),
            MessageHandler(filters.TEXT & filters.Regex(r"^◀️ Cancel$"), edittask_cancel),
        ],
        allow_reentry=True,
    )

