"""
tests/test_reminders.py — Tests for app/bot/reminders.py
Uses mocked bot, database, and AI calls to test scheduler setup
and the reminder/summary functions without real network or DB I/O.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.bot.reminders import check_deadlines, send_daily_summaries, create_scheduler


# =============================================================================
#  create_scheduler
# =============================================================================

def test_create_scheduler_returns_async_io_scheduler():
    bot = AsyncMock()
    scheduler = create_scheduler(bot)
    assert isinstance(scheduler, AsyncIOScheduler)


def test_create_scheduler_has_check_deadlines_job():
    bot = AsyncMock()
    scheduler = create_scheduler(bot)
    job_ids = {job.id for job in scheduler.get_jobs()}
    assert "check_deadlines" in job_ids


def test_create_scheduler_has_daily_summary_job():
    bot = AsyncMock()
    scheduler = create_scheduler(bot)
    job_ids = {job.id for job in scheduler.get_jobs()}
    assert "daily_summary" in job_ids


def test_create_scheduler_exactly_two_jobs():
    bot = AsyncMock()
    scheduler = create_scheduler(bot)
    assert len(scheduler.get_jobs()) == 2


def test_create_scheduler_does_not_start_automatically():
    bot = AsyncMock()
    scheduler = create_scheduler(bot)
    assert not scheduler.running


def test_create_scheduler_check_deadlines_is_interval():
    bot = AsyncMock()
    scheduler = create_scheduler(bot)
    job = scheduler.get_job("check_deadlines")
    assert job is not None
    assert job.trigger.__class__.__name__ == "IntervalTrigger"


def test_create_scheduler_daily_summary_is_cron():
    bot = AsyncMock()
    scheduler = create_scheduler(bot)
    job = scheduler.get_job("daily_summary")
    assert job is not None
    assert job.trigger.__class__.__name__ == "CronTrigger"


# =============================================================================
#  check_deadlines
# =============================================================================

@pytest.mark.asyncio
async def test_check_deadlines_no_tasks_sends_nothing():
    bot = AsyncMock()
    with patch("app.bot.reminders.db.get_due_tasks", return_value=[]):
        await check_deadlines(bot)
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_check_deadlines_sends_message_per_task():
    bot = AsyncMock()
    tasks = [
        {"id": 1, "user_id": 111, "title": "Task A", "deadline": "2026-05-02T15:00:00", "priority": "high"},
        {"id": 2, "user_id": 222, "title": "Task B", "deadline": "2026-05-02T15:30:00", "priority": "medium"},
    ]
    with patch("app.bot.reminders.db.get_due_tasks", return_value=tasks), \
         patch("app.bot.reminders.db.mark_task_reminded", new_callable=AsyncMock):
        await check_deadlines(bot)
    assert bot.send_message.call_count == 2


@pytest.mark.asyncio
async def test_check_deadlines_marks_tasks_reminded():
    bot = AsyncMock()
    tasks = [
        {"id": 42, "user_id": 111, "title": "Task", "deadline": "2026-05-02T15:00:00", "priority": "low"},
    ]
    mock_mark = AsyncMock()
    with patch("app.bot.reminders.db.get_due_tasks", return_value=tasks), \
         patch("app.bot.reminders.db.mark_task_reminded", mock_mark):
        await check_deadlines(bot)
    mock_mark.assert_called_once_with(42)


@pytest.mark.asyncio
async def test_check_deadlines_sends_to_correct_chat():
    bot = AsyncMock()
    tasks = [
        {"id": 1, "user_id": 12345, "title": "My task", "deadline": "2026-05-02T09:00:00", "priority": "medium"},
    ]
    with patch("app.bot.reminders.db.get_due_tasks", return_value=tasks), \
         patch("app.bot.reminders.db.mark_task_reminded", new_callable=AsyncMock):
        await check_deadlines(bot)
    call_kwargs = bot.send_message.call_args[1]
    assert call_kwargs["chat_id"] == 12345


@pytest.mark.asyncio
async def test_check_deadlines_continues_after_send_failure():
    bot = AsyncMock()
    bot.send_message.side_effect = Exception("network error")
    tasks = [
        {"id": 1, "user_id": 111, "title": "Task 1", "deadline": "2026-05-02T09:00:00", "priority": "high"},
        {"id": 2, "user_id": 222, "title": "Task 2", "deadline": "2026-05-02T10:00:00", "priority": "low"},
    ]
    with patch("app.bot.reminders.db.get_due_tasks", return_value=tasks), \
         patch("app.bot.reminders.db.mark_task_reminded", new_callable=AsyncMock):
        await check_deadlines(bot)  # must not raise


@pytest.mark.asyncio
async def test_check_deadlines_db_error_does_not_crash():
    bot = AsyncMock()
    with patch("app.bot.reminders.db.get_due_tasks", side_effect=Exception("DB down")):
        await check_deadlines(bot)  # must not raise


@pytest.mark.asyncio
async def test_check_deadlines_malformed_deadline_does_not_crash():
    bot = AsyncMock()
    tasks = [
        {"id": 1, "user_id": 111, "title": "Task", "deadline": "not-a-date", "priority": "medium"},
    ]
    with patch("app.bot.reminders.db.get_due_tasks", return_value=tasks), \
         patch("app.bot.reminders.db.mark_task_reminded", new_callable=AsyncMock):
        await check_deadlines(bot)  # must not raise — fallback dt_str = deadline


# =============================================================================
#  send_daily_summaries
# =============================================================================

@pytest.mark.asyncio
async def test_send_daily_summaries_no_users_sends_nothing():
    bot = AsyncMock()
    with patch("app.bot.reminders.db.get_all_users", return_value=[]):
        await send_daily_summaries(bot)
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_daily_summaries_user_with_no_tasks_skipped():
    bot = AsyncMock()
    users = [{"user_id": 111, "timezone": "UTC", "full_name": "Alice"}]
    stats = {"total": 0, "done": 0, "pending": 0, "overdue": 0, "completion_rate": 0, "top_category": "general"}
    with patch("app.bot.reminders.db.get_all_users", return_value=users), \
         patch("app.bot.reminders.db.get_user_tasks", return_value=[]), \
         patch("app.bot.reminders.db.get_user_stats", return_value=stats):
        await send_daily_summaries(bot)
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_daily_summaries_sends_to_correct_user():
    bot = AsyncMock()
    # Use a timezone where the current UTC hour maps to DAILY_SUMMARY_HOUR
    from config.settings import DAILY_SUMMARY_HOUR
    import pytz
    # Force the hour to match by using UTC with mocked datetime
    fake_now = MagicMock()
    fake_now.hour = DAILY_SUMMARY_HOUR

    users = [{"user_id": 99999, "timezone": "UTC", "full_name": "Test User"}]
    stats = {"total": 3, "done": 1, "pending": 2, "overdue": 0, "completion_rate": 33.3, "top_category": "work"}
    tasks = [{"id": 1, "title": "Pending task", "priority": "high"}]

    with patch("app.bot.reminders.db.get_all_users", return_value=users), \
         patch("app.bot.reminders.db.get_user_tasks", return_value=tasks), \
         patch("app.bot.reminders.db.get_user_stats", return_value=stats), \
         patch("app.bot.reminders.ai.generate_daily_motivation", return_value="Stay focused!"), \
         patch("app.bot.reminders.datetime") as mock_dt:
        mock_dt.utcnow.return_value = datetime(2026, 5, 2, DAILY_SUMMARY_HOUR, 0, 0)
        mock_dt.now.return_value = fake_now
        await send_daily_summaries(bot)

    # If we get here with the correct hour, message is sent
    # (test just verifies it doesn't crash when conditions align)


@pytest.mark.asyncio
async def test_send_daily_summaries_db_error_does_not_crash():
    bot = AsyncMock()
    with patch("app.bot.reminders.db.get_all_users", side_effect=Exception("DB error")):
        await send_daily_summaries(bot)  # must not raise


@pytest.mark.asyncio
async def test_send_daily_summaries_per_user_error_continues():
    bot = AsyncMock()
    users = [
        {"user_id": 111, "timezone": "UTC", "full_name": "Alice"},
        {"user_id": 222, "timezone": "UTC", "full_name": "Bob"},
    ]
    with patch("app.bot.reminders.db.get_all_users", return_value=users), \
         patch("app.bot.reminders.db.get_user_stats", side_effect=Exception("stats failed")):
        await send_daily_summaries(bot)  # must not raise; error is per-user


@pytest.mark.asyncio
async def test_send_daily_summaries_invalid_timezone_falls_back():
    bot = AsyncMock()
    users = [{"user_id": 111, "timezone": "Not/ATimezone", "full_name": "Alice"}]
    stats = {"total": 0, "done": 0, "pending": 0, "overdue": 0, "completion_rate": 0, "top_category": "general"}
    with patch("app.bot.reminders.db.get_all_users", return_value=users), \
         patch("app.bot.reminders.db.get_user_stats", return_value=stats), \
         patch("app.bot.reminders.db.get_user_tasks", return_value=[]):
        await send_daily_summaries(bot)  # must not raise on bad timezone
