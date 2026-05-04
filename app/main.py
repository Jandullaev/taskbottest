"""app/main.py — Application entry point."""

import logging

from app.core.logger import setup_logging
from config.settings import TELEGRAM_BOT_TOKEN, GEMINI_API_KEY

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import app.core.database as db
from app.bot.reminders import create_scheduler
from app.bot.handlers import (
    cmd_start,
    cmd_help,
    cmd_mytasks,
    cmd_mytask,
    cmd_done,
    cmd_deletetask,
    cmd_stats,
    cmd_settimezone,
    unknown_command,
    msg_handle_menu_mytasks,
    msg_handle_menu_stats,
    msg_handle_menu_filters,
    msg_handle_filter,
    msg_handle_menu_timezone,
    msg_handle_timezone,
    msg_back_to_menu,
    msg_handle_task_done,
    msg_handle_task_delete,
    msg_handle_task_delete_confirm,
    msg_handle_task_delete_cancel,
    callback_task_view,
    callback_main_menu,
)
from app.bot.conversations import (
    build_addtask_handler,
    build_addtask_ai_handler,
    build_edittask_handler,
)

setup_logging()
logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand("start", "Register and get started"),
    BotCommand("help",  "Show help"),
]


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log all exceptions and notify the user."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update):
        msg = (
            "⚠️ Something went wrong while processing your request\\.\n"
            "Please try again or use /help\\."
        )
        try:
            if update.callback_query:
                await update.callback_query.answer(
                    "Something went wrong. Please try again.", show_alert=True
                )
            elif update.effective_message:
                await update.effective_message.reply_text(msg, parse_mode="MarkdownV2")
        except Exception:
            pass


async def post_init(application: Application) -> None:
    await db.init_db()
    await application.bot.set_my_commands(BOT_COMMANDS)
    logger.info("Database initialised and bot commands registered.")

    scheduler = create_scheduler(application.bot)
    scheduler.start()
    application.bot_data["scheduler"] = scheduler
    logger.info("Reminder scheduler started.")


async def post_shutdown(application: Application) -> None:
    scheduler = application.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Reminder scheduler stopped.")


def main():
    token = TELEGRAM_BOT_TOKEN
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set.")

    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set — AI features will fail at runtime.")

    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # ── Conversation handlers (registered first — highest priority)
    app.add_handler(build_addtask_handler())
    app.add_handler(build_addtask_ai_handler())
    app.add_handler(build_edittask_handler())

    # ── Simple command handlers
    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("help",        cmd_help))
    app.add_handler(CommandHandler("mytasks",     cmd_mytasks))
    app.add_handler(CommandHandler("mytask",      cmd_mytask))
    app.add_handler(CommandHandler("done",        cmd_done))
    app.add_handler(CommandHandler("deletetask",  cmd_deletetask))
    app.add_handler(CommandHandler("stats",       cmd_stats))
    app.add_handler(CommandHandler("settimezone", cmd_settimezone))

    # ── Task action buttons  ← MUST come before filter buttons
    #    because "✅ Done" exists in both filter and task-action keyboards.
    #    The handler checks context.user_data["current_task_id"] to decide
    #    which path to take, so registration order matters here.
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^✅ Done$"), msg_handle_task_done
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^🗑️ Delete$"), msg_handle_task_delete
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^🗑️ Yes, Delete$"), msg_handle_task_delete_confirm
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^↩️ Cancel$"), msg_handle_task_delete_cancel
    ))

    # ── Main menu buttons
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^📋 My Tasks$"), msg_handle_menu_mytasks
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^📊 Stats$"), msg_handle_menu_stats
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^🔍 Filters$"), msg_handle_menu_filters
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^⚙️ Timezone$"), msg_handle_menu_timezone
    ))

    # ── Filter buttons (status / category)
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(
            r"^(⏳ Pending|🔄 In Progress|💼 Work|📚 Study|🏠 Personal|❤️ Health|💰 Finance)$"
        ),
        msg_handle_filter,
    ))

    # ── Timezone buttons
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^🌍"), msg_handle_timezone
    ))

    # ── Navigation
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^◀️ Back to Menu$"), msg_back_to_menu
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^❌ Cancel$"), msg_back_to_menu
    ))

    # ── Inline callbacks
    app.add_handler(CallbackQueryHandler(callback_task_view,  pattern=r"^task_view_\d+$"))
    app.add_handler(CallbackQueryHandler(callback_main_menu, pattern=r"^menu_main$"))

    # ── Unknown commands fallback
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # ── Global error handler
    app.add_error_handler(error_handler)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()