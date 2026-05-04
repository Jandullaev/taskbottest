"""
tests/test_database.py — Tests for app/core/database.py functions
using a real SQLite file via patched DB_PATH.
"""

import pytest
import pytest_asyncio
import aiosqlite
from unittest.mock import patch

import app.core.database as database


@pytest_asyncio.fixture
async def db_path(tmp_path):
    """Patch DB_PATH to a temp file and initialise the schema. Patch stays active during test."""
    path = str(tmp_path / "test.db")
    with patch("app.core.database.DB_PATH", path):
        await database.init_db()
        yield path


# =============================================================================
#  init_db
# =============================================================================

@pytest.mark.asyncio
async def test_init_db_creates_users_table(db_path):
    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ) as cur:
            assert await cur.fetchone() is not None


@pytest.mark.asyncio
async def test_init_db_creates_tasks_table(db_path):
    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
        ) as cur:
            assert await cur.fetchone() is not None


@pytest.mark.asyncio
async def test_init_db_is_idempotent(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.init_db()
        await database.init_db()  # second call must not raise


# =============================================================================
#  upsert_user / get_user
# =============================================================================

@pytest.mark.asyncio
async def test_upsert_inserts_new_user(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(1001, "alice", "Alice Smith")
        user = await database.get_user(1001)
    assert user is not None
    assert user["user_id"] == 1001
    assert user["username"] == "alice"
    assert user["full_name"] == "Alice Smith"


@pytest.mark.asyncio
async def test_upsert_sets_default_timezone(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(1002, "bob", "Bob")
        user = await database.get_user(1002)
    assert user["timezone"] == "UTC"


@pytest.mark.asyncio
async def test_upsert_updates_existing_user(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(1003, "old_name", "Old Full")
        await database.upsert_user(1003, "new_name", "New Full")
        user = await database.get_user(1003)
    assert user["username"] == "new_name"
    assert user["full_name"] == "New Full"


@pytest.mark.asyncio
async def test_get_user_nonexistent_returns_none(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        user = await database.get_user(9999)
    assert user is None


# =============================================================================
#  update_user_preferences
# =============================================================================

@pytest.mark.asyncio
async def test_update_timezone(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(2001, "carol", "Carol")
        await database.update_user_preferences(2001, timezone="Asia/Tashkent")
        user = await database.get_user(2001)
    assert user["timezone"] == "Asia/Tashkent"


@pytest.mark.asyncio
async def test_update_language(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(2002, "dave", "Dave")
        await database.update_user_preferences(2002, language="ru")
        user = await database.get_user(2002)
    assert user["language"] == "ru"


@pytest.mark.asyncio
async def test_update_no_fields_is_noop(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(2003, "eve", "Eve")
        await database.update_user_preferences(2003)
        user = await database.get_user(2003)
    assert user["timezone"] == "UTC"
    assert user["language"] == "en"


# =============================================================================
#  get_all_users
# =============================================================================

@pytest.mark.asyncio
async def test_get_all_users_empty(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        users = await database.get_all_users()
    assert users == []


@pytest.mark.asyncio
async def test_get_all_users_returns_all(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(3001, "u1", "User One")
        await database.upsert_user(3002, "u2", "User Two")
        users = await database.get_all_users()
    ids = {u["user_id"] for u in users}
    assert 3001 in ids
    assert 3002 in ids


# =============================================================================
#  create_task / get_task
# =============================================================================

@pytest.mark.asyncio
async def test_create_task_returns_positive_id(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(4001, "frank", "Frank")
        task_id = await database.create_task(4001, "Buy milk")
    assert isinstance(task_id, int)
    assert task_id > 0


@pytest.mark.asyncio
async def test_create_task_stores_all_fields(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(4002, "grace", "Grace")
        tid = await database.create_task(
            4002, "Write report", "Due Monday", "work", "high", "2026-06-01T09:00:00"
        )
        task = await database.get_task(tid, 4002)
    assert task["title"] == "Write report"
    assert task["description"] == "Due Monday"
    assert task["category"] == "work"
    assert task["priority"] == "high"
    assert task["deadline"] == "2026-06-01T09:00:00"


@pytest.mark.asyncio
async def test_create_task_defaults(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(4003, "heidi", "Heidi")
        tid = await database.create_task(4003, "Default task")
        task = await database.get_task(tid, 4003)
    assert task["status"] == "pending"
    assert task["category"] == "general"
    assert task["priority"] == "medium"
    assert task["deadline"] is None


@pytest.mark.asyncio
async def test_get_task_wrong_user_returns_none(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(4004, "ivan", "Ivan")
        tid = await database.create_task(4004, "Private task")
        result = await database.get_task(tid, 9999)
    assert result is None


@pytest.mark.asyncio
async def test_get_task_nonexistent_returns_none(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        result = await database.get_task(99999, 1)
    assert result is None


# =============================================================================
#  get_user_tasks
# =============================================================================

@pytest.mark.asyncio
async def test_get_user_tasks_returns_own_tasks(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(5001, "judy", "Judy")
        await database.create_task(5001, "Task A")
        await database.create_task(5001, "Task B")
        tasks = await database.get_user_tasks(5001)
    assert len(tasks) == 2


@pytest.mark.asyncio
async def test_get_user_tasks_excludes_other_users(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(5002, "karl", "Karl")
        await database.upsert_user(5003, "lea", "Lea")
        await database.create_task(5002, "Karl task")
        tasks = await database.get_user_tasks(5003)
    assert tasks == []


@pytest.mark.asyncio
async def test_get_user_tasks_filter_by_status(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(5004, "mike", "Mike")
        id1 = await database.create_task(5004, "Pending")
        id2 = await database.create_task(5004, "Done")
        await database.update_task(id2, 5004, status="done")
        pending = await database.get_user_tasks(5004, status="pending")
        done = await database.get_user_tasks(5004, status="done")
    assert len(pending) == 1 and pending[0]["title"] == "Pending"
    assert len(done) == 1 and done[0]["title"] == "Done"


@pytest.mark.asyncio
async def test_get_user_tasks_filter_by_category(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(5005, "nina", "Nina")
        await database.create_task(5005, "Work task", category="work")
        await database.create_task(5005, "Study task", category="study")
        tasks = await database.get_user_tasks(5005, category="work")
    assert len(tasks) == 1
    assert tasks[0]["category"] == "work"


@pytest.mark.asyncio
async def test_get_user_tasks_excludes_cancelled(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(5006, "oscar", "Oscar")
        id1 = await database.create_task(5006, "Normal")
        id2 = await database.create_task(5006, "Cancelled")
        await database.update_task(id2, 5006, status="cancelled")
        tasks = await database.get_user_tasks(5006)
    titles = [t["title"] for t in tasks]
    assert "Cancelled" not in titles
    assert "Normal" in titles


@pytest.mark.asyncio
async def test_get_user_tasks_priority_ordering(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(5007, "pat", "Pat")
        await database.create_task(5007, "Low task", priority="low")
        await database.create_task(5007, "High task", priority="high")
        await database.create_task(5007, "Med task", priority="medium")
        tasks = await database.get_user_tasks(5007)
    assert tasks[0]["priority"] == "high"
    assert tasks[1]["priority"] == "medium"
    assert tasks[2]["priority"] == "low"


# =============================================================================
#  update_task
# =============================================================================

@pytest.mark.asyncio
async def test_update_task_title(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(6001, "quinn", "Quinn")
        tid = await database.create_task(6001, "Original")
        result = await database.update_task(tid, 6001, title="Updated")
        task = await database.get_task(tid, 6001)
    assert result is True
    assert task["title"] == "Updated"


@pytest.mark.asyncio
async def test_update_task_status(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(6002, "rob", "Rob")
        tid = await database.create_task(6002, "Task")
        await database.update_task(tid, 6002, status="done")
        task = await database.get_task(tid, 6002)
    assert task["status"] == "done"


@pytest.mark.asyncio
async def test_update_task_multiple_fields(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(6003, "sara", "Sara")
        tid = await database.create_task(6003, "Task")
        await database.update_task(tid, 6003, priority="high", category="work")
        task = await database.get_task(tid, 6003)
    assert task["priority"] == "high"
    assert task["category"] == "work"


@pytest.mark.asyncio
async def test_update_task_wrong_user_returns_false(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(6004, "tom", "Tom")
        tid = await database.create_task(6004, "Secure task")
        result = await database.update_task(tid, 9999, title="Hacked")
    assert result is False


@pytest.mark.asyncio
async def test_update_task_no_allowed_fields_returns_false(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(6005, "uma", "Uma")
        tid = await database.create_task(6005, "Task")
        result = await database.update_task(tid, 6005, invalid_column="value")
    assert result is False


# =============================================================================
#  delete_task
# =============================================================================

@pytest.mark.asyncio
async def test_delete_task_removes_it(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(7001, "vera", "Vera")
        tid = await database.create_task(7001, "To delete")
        result = await database.delete_task(tid, 7001)
        task = await database.get_task(tid, 7001)
    assert result is True
    assert task is None


@pytest.mark.asyncio
async def test_delete_task_nonexistent_returns_false(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(7002, "will", "Will")
        result = await database.delete_task(99999, 7002)
    assert result is False


@pytest.mark.asyncio
async def test_delete_task_wrong_user_returns_false(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(7003, "xena", "Xena")
        tid = await database.create_task(7003, "Secure")
        result = await database.delete_task(tid, 9999)
    assert result is False


# =============================================================================
#  mark_task_reminded
# =============================================================================

@pytest.mark.asyncio
async def test_mark_task_reminded_sets_timestamp(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(8001, "yara", "Yara")
        tid = await database.create_task(8001, "Reminder task")
        await database.mark_task_reminded(tid)
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT reminded_at FROM tasks WHERE id = ?", (tid,)
            ) as cur:
                row = await cur.fetchone()
    assert row["reminded_at"] is not None


@pytest.mark.asyncio
async def test_mark_task_reminded_twice_does_not_raise(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(8002, "zack", "Zack")
        tid = await database.create_task(8002, "Task")
        await database.mark_task_reminded(tid)
        await database.mark_task_reminded(tid)


# =============================================================================
#  get_user_stats
# =============================================================================

@pytest.mark.asyncio
async def test_stats_empty_user(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(9001, "amy", "Amy")
        stats = await database.get_user_stats(9001)
    assert stats["total"] == 0
    assert stats["done"] == 0
    assert stats["pending"] == 0
    assert stats["completion_rate"] == 0.0


@pytest.mark.asyncio
async def test_stats_completion_rate(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(9002, "ben", "Ben")
        id1 = await database.create_task(9002, "T1", category="work")
        id2 = await database.create_task(9002, "T2", category="work")
        id3 = await database.create_task(9002, "T3", category="study")
        await database.update_task(id1, 9002, status="done")
        await database.update_task(id2, 9002, status="done")
        stats = await database.get_user_stats(9002)
    assert stats["total"] == 3
    assert stats["done"] == 2
    assert stats["pending"] == 1
    assert stats["completion_rate"] == pytest.approx(66.7, abs=0.1)


@pytest.mark.asyncio
async def test_stats_top_category(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(9003, "cara", "Cara")
        await database.create_task(9003, "W1", category="work")
        await database.create_task(9003, "W2", category="work")
        await database.create_task(9003, "S1", category="study")
        stats = await database.get_user_stats(9003)
    assert stats["top_category"] == "work"


@pytest.mark.asyncio
async def test_stats_all_done_rate_100(db_path):
    with patch("app.core.database.DB_PATH", db_path):
        await database.upsert_user(9004, "dan", "Dan")
        id1 = await database.create_task(9004, "Only task")
        await database.update_task(id1, 9004, status="done")
        stats = await database.get_user_stats(9004)
    assert stats["completion_rate"] == 100.0
