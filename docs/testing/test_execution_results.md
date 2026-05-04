# Test Execution Results

---

## Run 2 — May 3, 2026 (Bug-Fix Release)

### Executive Summary

✅ **ALL AUTOMATED TESTS PASSING** — 353/353
- **Duration:** ~4.5 seconds
- **Coverage:** 81% overall
- **Purpose:** Regression check after manual testing and bug-fix cycle
- **Manual Test Cycle:** 75 test cases executed; 13 failures identified and fixed

---

### Automated Test Suite Results

| Module | Tests | Pass | Fail | Coverage |
|---|---|---|---|---|
| `test_ai_service.py` | 41 | 41 | 0 | 79% |
| `test_database.py` | 38 | 38 | 0 | 73% |
| `test_formatters.py` | ~40 | ~40 | 0 | 97% |
| `test_handlers.py` | ~80 | ~80 | 0 | 99% |
| `test_keyboards.py` | 55 | 55 | 0 | 100% |
| `test_conversations.py` | ~120 | ~120 | 0 | 98% |
| `test_reminders.py` | 28 | 28 | 0 | 95% |
| **Total** | **353** | **353** | **0** | **81%** |

```
Name                           Stmts   Miss  Cover
--------------------------------------------------
app/bot/conversations.py         299      5    98%
app/bot/handlers.py              346      4    99%
app/bot/keyboards.py              30      0   100%
app/bot/reminders.py              66      3    95%
app/core/database.py             161     44    73%
app/core/formatters.py            67      2    97%
app/services/ai_service.py       126     26    79%
--------------------------------------------------
TOTAL                           1241    230    81%
```

---

### Manual Test Execution Summary

75 manual test cases were executed against a live bot instance. Results:

| Result | Count |
|---|---|
| ✅ Pass | 50 |
| ❌ Fail | 13 |
| ⬜ Not Run | 12 |

---

### Bugs Found and Fixed

The following 8 defects were identified during manual testing and resolved in this cycle. Test cases that were marked **Passed with an Actual Result noting a bug** are included — the tester observed the bug but the test technically completed (no crash), so it was recorded as Passed. All defects are now fixed and confirmed.

---

#### BUG-01 — Menu keyboard disappears after wizard cancel
**Affected test cases:** TC_UI_008 (Failed), TC_UI_040 (Passed — keyboard disappearance noted)
**Root cause:** Cancel handlers in `conversations.py` sent a keyboard-bearing message then immediately deleted it. Telegram removes the reply keyboard when its carrier message is deleted.
**Fix:** Replaced the invisible-character + delete pattern with a visible `"❌ Cancelled."` message that is not deleted, keeping the keyboard visible.
**Files changed:** `app/bot/conversations.py` — `addtask_cancel`, `addtask_ai_cancel`, `edittask_cancel`
**Status after fix:** ✅ Re-tested — keyboard remains visible after cancel

---

#### BUG-02 — Edit inline keyboards not shown for Category, Priority, Status
**Affected test cases:** TC_UI_035, TC_UI_036, TC_UI_037 (all Failed), TC_UI_025 (Failed — side-effect)
**Root cause (two issues):**
1. `callback_task_edit` (the `✏️ Edit` inline button handler) was defined but never registered in the ConversationHandler entry_points — tapping the Edit button had no effect.
2. `callback_task_edit` used `_safe_edit(..., reply_markup=_edit_field_keyboard())` where `_edit_field_keyboard()` is a `ReplyKeyboardMarkup`. The Telegram API's `editMessageText` only accepts `InlineKeyboardMarkup`; passing a reply keyboard caused a silent failure.
**Fix:**
- Added `_edit_field_inline_keyboard()` — an inline version of the field selector.
- Fixed `callback_task_edit` to use the inline keyboard and registered it in `build_edittask_handler` entry_points.
- Added `CallbackQueryHandler(callback_edit_field, pattern=r"^ef_")` to the `EDIT_FIELD` state so inline field selections are properly handled.
**Files changed:** `app/bot/conversations.py`
**Status after fix:** ✅ Re-tested — Category, Priority, Status inline buttons appear correctly; In Progress filter now works after tasks can be set to in_progress

---

#### BUG-03 — Invalid deadline input silently ignored in edit flow
**Affected test cases:** TC_UI_039 (Passed — no error shown, noted in Actual Result)
**Root cause:** In `edittask_value`, when a deadline parse error occurs, `_safe_edit` was called on `edit_orig_msg`. If that reference was `None` (conversation not started correctly, linked to BUG-02), `_safe_edit(None, ...)` raised an `AttributeError` that was swallowed by the global error handler — the user saw nothing.
**Fix:** Added a null guard: if `edit_orig_msg` is available, use `_safe_edit`; otherwise fall back to `send_message` to always show the error to the user.
**Files changed:** `app/bot/conversations.py` — `edittask_value`
**Status after fix:** ✅ Re-tested — invalid deadline shows error message and re-prompts

---

#### BUG-04 — Timezone not applied to deadline display
**Affected test cases:** TC_UI_010 (Passed — UTC display noted), TC_UI_057 (Passed — no change noted), TC_UI_059 (Passed — UTC display noted)
**Root cause:** `fmt_deadline()` and `format_task_card()` in `formatters.py` had no timezone parameter. Deadlines stored as UTC ISO strings were formatted and displayed as UTC regardless of the user's saved timezone.
**Fix:**
- Added `tz_name: str = "UTC"` parameter to `fmt_deadline` and `user_tz: str = "UTC"` to `format_task_card`.
- `fmt_deadline` now converts the UTC deadline to the user's timezone using `pytz` before formatting.
- All callers of `format_task_card` in `handlers.py` and `conversations.py` now fetch the user's timezone from the DB and pass it through.
**Files changed:** `app/core/formatters.py`; `app/bot/handlers.py` — `cmd_mytask`, `callback_task_view`, `msg_handle_task_done`, `msg_handle_task_delete_cancel`; `app/bot/conversations.py` — `_finish_addtask`, `addtask_ai_input`, `_apply_edit`
**Status after fix:** ✅ Re-tested — deadlines display in user's local timezone

---

#### BUG-05 — `/deletetask` command loses task context at confirmation
**Affected test cases:** TC_UI_050 (Passed — "No task selected" error noted)
**Root cause:** `cmd_deletetask` sent the confirmation keyboard but never stored `task_id` in `context.user_data["delete_task_id"]`. When the user tapped "Yes, Delete", `msg_handle_task_delete_confirm` found `None` and responded with "⚠️ No task selected."
**Fix:** Added `context.user_data["delete_task_id"] = task_id` and `context.user_data["delete_msg"] = msg` in `cmd_deletetask` after verifying the task exists, matching the pattern used by the inline button path.
**Files changed:** `app/bot/handlers.py` — `cmd_deletetask`
**Status after fix:** ✅ Re-tested — `/deletetask <id>` followed by confirmation now deletes the task correctly

---

#### BUG-06 — `/done` command has no idempotency check
**Affected test cases:** TC_UI_045 (Passed — duplicate confirmation noted in Actual Result)
**Root cause:** `cmd_done` called `db.update_task(..., status="done")` unconditionally without first checking if the task was already in `done` status. The inline button handler `msg_handle_task_done` had this guard but the command alias did not.
**Fix:** Added the same `if task["status"] == "done"` check before the DB update, responding with an informational message and returning early.
**Files changed:** `app/bot/handlers.py` — `cmd_done`
**Status after fix:** ✅ Re-tested — `/done <id>` on an already-done task returns "already marked as done"

---

#### BUG-07 — Deadline reminders never fired
**Affected test cases:** TC_UI_062 (Passed — no reminder received, timezone note added)
**Root cause:** Deadlines are stored as `"2026-05-03T09:00:00"` (ISO 8601 with `T` separator via `datetime.utcnow().isoformat()`). SQLite's `datetime('now')` returns `"2026-05-03 09:00:00"` (space separator). Because SQLite stores deadlines as TEXT and compares them lexicographically, the character `T` (ASCII 84) is greater than space (ASCII 32), so every stored deadline always evaluated as "in the future" — the 30-minute window condition was never satisfied and no reminders were ever sent. The same bug affected `reminded_at` de-duplication.
**Fix:** Replaced `datetime('now', ...)` with `strftime('%Y-%m-%dT%H:%M:%S', 'now', ...)` in the `get_due_tasks` query so both sides of the comparison use the same `T`-separated ISO format.
**Files changed:** `app/core/database.py` — `get_due_tasks`
**Status after fix:** ✅ Re-tested — reminders fire correctly within the 30-minute window

---

#### BUG-08 — In Progress filter returned no results
**Affected test cases:** TC_UI_025 (Failed)
**Root cause:** Dependent on BUG-02. There was no way to set a task's status to `in_progress` through the UI because the Edit → Status inline keyboard was never shown. The filter itself is correctly implemented; it simply had no matching data.
**Fix:** Resolved as a side effect of BUG-02 fix. Once the Status edit inline keyboard works, tasks can be set to `in_progress`, and the filter returns them correctly.
**Files changed:** None (fix is in BUG-02)
**Status after fix:** ✅ Re-tested — In Progress filter works after setting a task via Edit → Status

---

### Test Case Status Updates

The following test cases had **Status: Passed** with an **Actual Result** documenting a bug. These are now fixed and the bugs are resolved:

| Test ID | Issue Noted in Actual Result | Bug Fixed | New Status |
|---|---|---|---|
| TC_UI_010 | Deadline displayed in UTC regardless of timezone | BUG-04 | ✅ Fixed |
| TC_UI_039 | Invalid deadline silently ignored — no error shown | BUG-03 | ✅ Fixed |
| TC_UI_040 | Edit cancel returns to menu but keyboard closes immediately | BUG-01 | ✅ Fixed |
| TC_UI_045 | `/done` confirms task as done even when already done | BUG-06 | ✅ Fixed |
| TC_UI_050 | "⚠️ No task selected." shown after `/deletetask` confirmation | BUG-05 | ✅ Fixed |
| TC_UI_057 | Timezone success message shown but deadline display unchanged | BUG-04 | ✅ Fixed |
| TC_UI_059 | Deadline display does not change after timezone switch | BUG-04 | ✅ Fixed |
| TC_UI_062 | No reminder notification fired | BUG-07 | ✅ Fixed |

The following test cases had **Status: Failed** and are now fixed:

| Test ID | Issue | Bug Fixed | New Status |
|---|---|---|---|
| TC_UI_008 | Menu keyboard disappears after wizard cancel | BUG-01 | ✅ Fixed |
| TC_UI_025 | In Progress filter returned no results | BUG-08 (via BUG-02) | ✅ Fixed |
| TC_UI_035 | No inline keyboard shown when editing Category | BUG-02 | ✅ Fixed |
| TC_UI_036 | No inline keyboard shown when editing Priority | BUG-02 | ✅ Fixed |
| TC_UI_037 | No inline keyboard shown when editing Status | BUG-02 | ✅ Fixed |

---

### Outstanding Items (Not Run)

The following 12 test cases remain **Not Run** and require a live environment or specific timing to execute:

| Test ID | Reason |
|---|---|
| TC_UI_032 | Requires two separate Telegram accounts |
| TC_UI_052 | Requires two separate Telegram accounts |
| TC_UI_063 | Depends on TC_UI_062 passing first; requires wait |
| TC_UI_064 | Requires wait for scheduler cycle |
| TC_UI_065 | Requires waiting until 9 AM user-local time |
| TC_UI_066 | Requires waiting until 9 AM with all tasks completed |
| TC_UI_067 | Requires rapid multi-tap input |
| TC_UI_068 | Pending execution |
| TC_UI_069 | Pending execution |
| TC_UI_070 | Requires disabling Gemini API key |
| TC_UI_071 | Pending execution |
| TC_UI_072 | Requires creating 50 tasks |
| TC_UI_073 | Requires concurrent sessions |

---

### Metrics Comparison

| Metric | Run 1 (May 2) | Run 2 (May 3) | Change |
|---|---|---|---|
| **Automated Tests** | 353 / 353 | 353 / 353 | — |
| **Coverage (overall)** | 82% | 81% | -1pp (new code added) |
| `conversations.py` | 99% | 98% | -1pp |
| `handlers.py` | 100% | 99% | -1pp |
| `formatters.py` | 98% | 97% | -1pp |
| **Manual Tests Run** | 0 | 63 / 75 | +63 |
| **Manual Tests Passed** | — | 50 | — |
| **Manual Tests Failed** | — | 13 → **0** | All fixed |
| **Bugs Found** | 0 | 8 | — |
| **Bugs Fixed** | 0 | **8** | 100% fix rate |

> Coverage decreased by 1pp because new code was added (timezone handling, inline field keyboard, null guards, idempotency checks) and not all new branches are exercised by existing unit tests.

---

### Issues Resolved in This Cycle

| ID | Description | Files Changed |
|---|---|---|
| BUG-01 | Menu keyboard disappears after cancel | `conversations.py` |
| BUG-02 | Edit inline keyboards (Category/Priority/Status) not shown | `conversations.py` |
| BUG-03 | Invalid deadline silently ignored in edit flow | `conversations.py` |
| BUG-04 | Timezone not applied to deadline display | `formatters.py`, `handlers.py`, `conversations.py` |
| BUG-05 | `/deletetask` command loses task context at confirmation | `handlers.py` |
| BUG-06 | `/done` command has no idempotency check | `handlers.py` |
| BUG-07 | Deadline reminders never fired (ISO date format mismatch in SQLite) | `database.py` |
| BUG-08 | In Progress filter broken (dependent on BUG-02) | *(no direct change)* |

---

**Generated:** May 3, 2026

---

---

## Run 1 — May 2, 2026 (Initial Full Coverage Run)

**Date:** May 2, 2026

---

### Executive Summary

✅ **ALL TESTS PASSING** — 353/353 tests executed successfully
- **Duration:** ~4 seconds
- **Coverage:** 82% overall (up from 41%); critical modules at 95–100%
- **Status:** Full unit + integration test suite — exceeds 80% industry standard

---

### Test Suite Breakdown

#### 1. AI Service Tests (41 tests)
**File:** `tests/test_ai_service.py`

| Test Class / Area | Tests | Status | Notes |
|---|---|---|---|
| TestSafeJson | 10 | ✅ PASS | JSON extraction, markdown fences, embedded JSON |
| TestCountTokens | 6 | ✅ PASS | Token estimation, length proportionality |
| TestTokenTracker | 13 | ✅ PASS | Accumulation, cost calculation, stats output |
| parse_task_from_text | 7 | ✅ PASS | Mocked _gemini; category/priority defaults |
| auto_categorize | 5 | ✅ PASS | All valid categories, trailing period stripping |
| predict_priority | 6 | ✅ PASS | All valid priorities, deadline param, exceptions |
| generate_daily_motivation | 3 | ✅ PASS | Normal response and fallback string |

---

#### 2. Database Tests (38 tests)
**File:** `tests/test_database.py`

| Area | Tests | Status | Notes |
|---|---|---|---|
| init_db | 3 | ✅ PASS | Tables created, idempotent |
| upsert_user / get_user | 4 | ✅ PASS | Insert, update, defaults, not-found |
| update_user_preferences | 3 | ✅ PASS | Timezone, language, no-op |
| get_all_users | 2 | ✅ PASS | Empty list, multiple users |
| create_task / get_task | 5 | ✅ PASS | All fields, defaults, user isolation |
| get_user_tasks | 6 | ✅ PASS | Filtering, ordering, cancelled exclusion |
| update_task | 5 | ✅ PASS | Single field, multiple fields, wrong user |
| delete_task | 3 | ✅ PASS | Success, not-found, wrong user |
| mark_task_reminded | 2 | ✅ PASS | Timestamp set, idempotent |
| get_user_stats | 4 | ✅ PASS | Empty user, completion rate, top category |

**Implementation note:** All tests call the actual `database.py` functions through a patched `DB_PATH` pointing to a temporary SQLite file — no raw SQL, full function coverage.

---

#### 3. Formatter Tests
**File:** `tests/test_formatters.py`

Coverage: **98%** — one unreachable branch in `format_task_card` (line 82).

---

#### 4. Handler Tests (~80 tests)
**File:** `tests/test_handlers.py`

| Area | Tests | Status | Notes |
|---|---|---|---|
| _delete | 4 | ✅ PASS | None input, success, exception swallowing |
| _safe_edit | 9 | ✅ PASS | Success, swallowed errors (both forms), re-raise |
| State constants | 2 | ✅ PASS | Unique values, EDIT_FIELDS completeness |
| Timezone / filter maps | 5 | ✅ PASS | UTC/Tashkent entries, status+category filters |
| cmd_start | 4 | ✅ PASS | New user, returning user, None username/full_name |
| cmd_help | 1 | ✅ PASS | Sends help message |
| msg_handle_menu_* | 6 | ✅ PASS | All 6 menu routing handlers |
| msg_handle_filter | 3 | ✅ PASS | Valid status, category, unknown filter |
| msg_handle_timezone | 3 | ✅ PASS | Valid TZ, unknown button, pytz error |
| msg_back_to_menu | 1 | ✅ PASS | Sends invisible char, deletes, sends menu |
| _render_task_list | 4 | ✅ PASS | Empty list, single, multiple, cancelled excluded |
| cmd_mytasks | 5 | ✅ PASS | No tasks, status filter, category filter, page |
| cmd_mytask / callback_task_view | 7 | ✅ PASS | Not found, wrong user, valid, stale callback |
| msg_handle_task_done | 4 | ✅ PASS | No task, not found, already done, success |
| msg_handle_task_edit | 3 | ✅ PASS | No task, not found, shows edit menu |
| msg_handle_task_delete | 3 | ✅ PASS | No task, not found, confirm prompt |
| msg_handle_task_delete_confirm/cancel | 6 | ✅ PASS | Confirm (success+fail), cancel |
| cmd_done | 4 | ✅ PASS | No args, not found, already done, success |
| cmd_deletetask | 4 | ✅ PASS | No args, not found, not found via id, success |
| cmd_stats | 2 | ✅ PASS | No stats, full stats with AI motivation |
| cmd_settimezone / callback_main_menu | 3 | ✅ PASS | Shows timezone menu, resets to main |
| unknown_command | 1 | ✅ PASS | Sends unknown command message |

Coverage: **100%**

---

#### 5. Keyboard Tests (55 tests)
**File:** `tests/test_keyboards.py`

| Keyboard | Tests | Status | Notes |
|---|---|---|---|
| main_menu_keyboard | 8 | ✅ PASS | All 6 buttons, resize, type |
| back_keyboard | 3 | ✅ PASS | Type, button label, count |
| filters_keyboard | 9 | ✅ PASS | All status+category filters incl. ✅ Done |
| timezone_keyboard | 6 | ✅ PASS | Globe prefix, back button, row width |
| task_action_keyboard | 5 | ✅ PASS | Done/Edit/Delete/Back buttons |
| delete_confirm_keyboard | 4 | ✅ PASS | Confirm and cancel, count |
| task_list_keyboard | 7 | ✅ PASS | Inline type, callback data, truncation |
| _edit_field_keyboard | 5 | ✅ PASS | All 6 fields, cancel button |

Coverage: **100%**

---

#### 6. Conversations Tests (~120 tests)
**File:** `tests/test_conversations.py`

| Area | Tests | Status | Notes |
|---|---|---|---|
| Keywords (today/tomorrow/next week) | 5 | ✅ PASS | Output dates and default 09:00 |
| Relative (in N days/hours/weeks) | 7 | ✅ PASS | Correct delta, time preservation for hours |
| Weekday names | 5 | ✅ PASS | All 7 days, same-day → next week |
| Absolute formats | 11 | ✅ PASS | ISO, slash, dot, dash, US-MDY formats |
| Error paths | 4 | ✅ PASS | Garbage, empty, partial, hint content |
| Wizard inline keyboards | 9 | ✅ PASS | category/priority/skip buttons and counts |
| _wz_edit | 3 | ✅ PASS | Noop, edit success, fallback on edit failure |
| addtask wizard (start→finish) | 15 | ✅ PASS | All 10 step functions, cancel, AI path |
| addtask_ai wizard | 5 | ✅ PASS | Start, input success/failure, cancel |
| edittask wizard | 18 | ✅ PASS | All 9 functions: start, field select, value inline/text |

Coverage: **99%** (4 unreachable exception branches in edge cases)

---

#### 7. Reminder Tests (28 tests)
**File:** `tests/test_reminders.py`

| Area | Tests | Status | Notes |
|---|---|---|---|
| create_scheduler | 7 | ✅ PASS | Returns AsyncIOScheduler, 2 jobs, correct trigger types |
| check_deadlines | 7 | ✅ PASS | Empty tasks, message count, mark_reminded, chat_id, failures |
| send_daily_summaries | 6 | ✅ PASS | No users, zero-task skip, DB error, per-user error, bad timezone |

Coverage: **95%**

---

### Code Coverage Report

```
Name                           Stmts   Miss  Cover
--------------------------------------------------
app/__init__.py                    0      0   100%
app/bot/__init__.py                0      0   100%
app/bot/constants.py              49     49     0%   (constants file, no logic)
app/bot/conversations.py         294      4    99%   ✅
app/bot/handlers.py              331      0   100%   ✅
app/bot/keyboards.py              30      0   100%   ✅
app/bot/reminders.py              66      3    95%   ✅
app/core/__init__.py               0      0   100%
app/core/database.py             161     44    73%   ✅
app/core/formatters.py            61      1    98%   ✅
app/core/logger.py                23     23     0%   (logging setup, no testable logic)
app/main.py                       74     74     0%   (entry point, requires full integration)
app/services/__init__.py           0      0   100%
app/services/ai_service.py       126     26    79%   ✅
--------------------------------------------------
TOTAL                           1215    224    82%
```

**Key improvements vs previous run (41% → 82%):**
- `handlers.py`: 18% → **100%** (+82pp)
- `conversations.py`: 27% → **99%** (+72pp)
- `formatters.py`: 90% → **98%** (+8pp)
- Excludes: `constants.py` (no logic), `logger.py` (logging setup), `main.py` (entry point) — these would need full integration tests to cover

---

### Fixtures Available

| Fixture | Scope | Purpose |
|---|---|---|
| `event_loop` | session | Single async event loop for all tests |
| `temp_db` | function | In-memory SQLite with full schema |
| `db_path` | function | Real SQLite temp file with patched DB_PATH |
| `mock_gemini_api` | function | Mocked Google Gemini client |
| `mock_bot` | function | Mocked Telegram bot |
| `sample_user` | function | Test user dict |
| `sample_task` | function | Test task dict |
| `sample_stats` | function | Test stats dict |

---

### Issues Resolved

#### ✅ Fix: "Message can't be edited" swallowed in _safe_edit
The error string `"message can't be edited"` was not caught (only the longer form `"can not"` was). Fixed by adding the apostrophe variant to the condition.

#### ✅ Fix: Add Task wizard silently stalling
`_wz_edit` was calling `_safe_edit` which swallowed the edit error — wizard advanced state but showed no visual update. Rewrote `_wz_edit` to try `edit_text` directly, catch any exception, delete old message, and resend.

#### ✅ Fix: "✅ Done" filter missing from filters_keyboard
The button was in `_FILTER_MAP` and handled, but never added to the keyboard layout. Added to `filters_keyboard()`.

#### ✅ Fix: "✅ Done" filter accidentally marking tasks done
`current_task_id` was not cleared when entering the filter view, so `msg_handle_task_done` used the stale task ID. Fixed in `msg_handle_menu_filters`.

#### ✅ Fix: Back to Menu sending visible message
Used `chr(0x3164)` (Hangul Filler) to satisfy Telegram's non-empty text check while rendering invisibly, immediately deleted after sending to switch the reply keyboard.

#### ✅ Fix: `back_keyboard` not imported in conversations.py
`edittask_start` called `back_keyboard()` which was missing from the `keyboards` import. Exposed by new tests; fixed by adding it to the import line.

---

### Test Metrics Summary

| Metric | Previous | Current | Status |
|---|---|---|---|
| **Total Tests** | 256 | **353** | ✅ +97 tests |
| **Passed** | 256 | **353** | ✅ 100% |
| **Failed** | 0 | **0** | ✅ |
| **Test Execution Time** | ~3.5s | **~4s** | ✅ FAST |
| **Overall Coverage** | **41%** | **82%** | ✅ +41pp — exceeds 80% threshold |
| **handlers.py** | 18% | **100%** | ✅ |
| **conversations.py** | 27% | **99%** | ✅ |
| **keyboards.py** | 100% | **100%** | ✅ |
| **reminders.py** | 95% | **95%** | ✅ |
| **ai_service.py** | 79% | **79%** | ✅ |
| **database.py** | 73% | **73%** | ✅ |
| **formatters.py** | 90% | **98%** | ✅ |

---

### Next Steps

1. **Integration tests for `main.py`** — wire up a full PTB Application in test mode to cover the entry point and handler registration
2. **`get_due_tasks` coverage** — write a test that inserts near-deadline tasks and calls `get_due_tasks` via patched DB_PATH (would push `database.py` from 73% to ~85%)
3. **`ai_service.py` branch coverage** — cover the token-budget-exceeded path and streaming fallback to push from 79% to ~90%

**Generated:** May 2, 2026
