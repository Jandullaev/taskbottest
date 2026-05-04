# Test Strategy & Test Plan

## Test Strategy

### Purpose

This test strategy defines the overall approach for testing the TaskBot Telegram bot application. It covers verification of:
- Individual function components and modules
- Integration between bot commands and the database
- End-to-end bot workflows and user interactions
- All features work as expected in the Telegram UI
- Database operations, AI service responses, and reminder scheduling
- Data formatting and output validation

### Scope

#### What is Tested
- **Database module (database.py)**: All CRUD operations and query functions
- **AI Service (ai_service.py)**: All 4 functions for task summarization and AI-powered features
- **Formatters (formatters.py)**: All 6 formatting functions for message output
- **Bot Handlers (handlers.py)**: All 10 bot commands
- **Reminders (reminders.py)**: Scheduler job functionality and reminder execution
- **Integration**: Bot commands working with database and external services

#### What is NOT Tested
- Telegram API internals and framework behavior
- OpenAI model accuracy and training
- Third-party library implementations
- Network infrastructure outside of the bot

### Test Levels

#### Unit Testing
- Individual functions in isolation
- Database operations (queries, inserts, updates, deletes)
- AI service response processing
- Formatter functions with various input types
- Error handling and edge cases
- Mock external dependencies

#### Integration Testing
- Bot commands executing with database interactions
- Command handlers connecting to AI service
- Reminder scheduler triggering database updates
- Data flow between modules
- Error propagation and recovery

#### System Testing
- Full end-to-end bot flow on deployed server
- User interactions via Telegram UI
- Real database operations
- Reminder execution in production environment
- External service interactions

#### Manual Testing
- Telegram UI interactions and user experience
- Command execution through Telegram client
- Message display and formatting verification
- Button interactions and inline keyboards
- Real-time reminder notifications
- Edge cases through manual input

### Test Approach

#### Automated Testing
- **Framework**: pytest for unit and integration tests
- **Async Support**: pytest-asyncio for async function testing
- **Database Testing**: Real SQLite temp file per test via patched `DB_PATH` (`unittest.mock.patch`)
- **Mocking**: `unittest.mock.patch` for `_gemini` (Gemini AI), `db.*` functions in reminders
- **Coverage**: Core modules (keyboards, reminders, database, ai_service) at 73–100%; overall 41%

#### Manual Testing
- **Platform**: Telegram mobile and web clients
- **Testers**: Solo developer testing all features
- **Execution**: Command execution and response verification
- **User Experience**: Validate output formatting and usability

### Test Environment

#### Local Development
- **Machine**: Development workstation (Windows/Linux/macOS)
- **Database**: SQLite test database
- **Purpose**: Unit and integration testing
- **Dependencies**: pytest, pytest-asyncio, test fixtures

#### Deployed Server
- **Infrastructure**: Production Telegram bot server
- **Database**: Production SQLite database or staging copy
- **Purpose**: System testing and end-to-end validation
- **User**: Real or test Telegram user account

### Test Data

#### Predefined Test Users
- Test user accounts with various permission levels
- Users with no tasks, few tasks, and many tasks
- Users with different task completion rates

#### Predefined Test Tasks
- Simple single-word tasks
- Long descriptive tasks
- Tasks with special characters and Unicode
- Tasks with different priority levels
- Overdue tasks and future-dated tasks

#### Edge Case Inputs
- Empty strings and whitespace-only inputs
- Very long inputs (>1000 characters)
- Special characters and emoji
- Malformed dates and invalid formats
- Boundary values (min/max task counts)
- Concurrent operations on same data

### Entry and Exit Criteria

#### Entry Criteria
- Code changes are complete and reviewed
- Code is stable and compile/syntax errors resolved
- All changes are pushed to GitHub repository
- Development environment is set up and functional
- Test environment and data are prepared

#### Exit Criteria
- All critical test cases pass (100% pass rate)
- No critical or high-severity bugs remaining
- Test coverage meets minimum threshold (>80%)
- Test report is documented and reviewed
- Performance meets acceptable baseline
- Known limitations are documented

---

## Test Plan

### Test Objectives

- **Verify Functionality**: Ensure all 10 bot commands work as designed
- **Verify Data Integrity**: Confirm database CRUD operations maintain data consistency
- **Verify AI Integration**: Validate AI service produces appropriate responses
- **Verify User Experience**: Ensure bot responds correctly through Telegram UI
- **Verify Reliability**: Confirm reminder scheduling and execution work reliably
- **Identify Defects**: Find and document any bugs or unexpected behavior
- **Establish Baseline**: Create reproducible test results for regression testing

### Test Scope

#### In Scope
- All 10 bot commands functionality
- Database CRUD operations (Create, Read, Update, Delete)
- AI service integration and response quality
- Reminder scheduling and execution
- Message formatters and output display
- Error handling and recovery
- Data validation and edge cases

#### Out of Scope
- Telegram API library internals and framework
- OpenAI API accuracy and model behavior
- Network protocol implementations
- Operating system-level dependencies
- Third-party library bugs or limitations

### Test Schedule

| Phase | Component | Start Date | End Date | Duration |
|-------|-----------|-----------|----------|----------|
| Unit Testing | database.py, ai_service.py, formatters.py | March 13 | March 15 | 3 days |
| Integration Testing | handlers.py with database, reminders.py | March 15 | March 17 | 2 days |
| System Testing | Full bot flow, Telegram UI | March 17 | March 19 | 2 days |
| Test Reporting | Documentation and reporting | March 19 | March 23 | 4 days |

### Test Items

#### Module: database.py (`app/core/database.py`)
- `init_db()` — schema creation, idempotency
- `upsert_user()` — insert new user, update existing
- `get_user()` — retrieval by ID, not-found case
- `update_user_preferences()` — timezone/language update, no-op on empty
- `get_all_users()` — empty list, multiple users
- `create_task()` — all fields, defaults, returns new ID
- `get_task()` — retrieval, wrong-user isolation
- `get_user_tasks()` — status/category filters, priority ordering, cancelled exclusion
- `update_task()` — single/multiple fields, wrong user, unknown fields
- `delete_task()` — success, not-found, wrong user
- `mark_task_reminded()` — sets reminded_at, idempotent
- `get_user_stats()` — totals, completion rate, top category

#### Module: ai_service.py (`app/services/ai_service.py`)
- `_safe_json()` — valid JSON, markdown fences, embedded JSON, invalid input
- `count_tokens()` — returns int, proportional to length
- `TokenTracker` — accumulation, cost calculation, stats string
- `parse_task_from_text()` — mocked Gemini; category/priority defaults on invalid values
- `auto_categorize()` — all 6 categories, trailing period, exception fallback
- `predict_priority()` — all 3 priorities, deadline param, exception fallback
- `generate_daily_motivation()` — response passthrough, exception fallback

#### Module: keyboards.py (`app/bot/keyboards.py`)
- `main_menu_keyboard()` — all 6 buttons present
- `back_keyboard()` — back button
- `filters_keyboard()` — all status + category filters including ✅ Done
- `timezone_keyboard()` — globe prefix, UTC, back button
- `task_action_keyboard()` — Done/Edit/Delete/Back
- `delete_confirm_keyboard()` — Yes/Cancel buttons
- `task_list_keyboard()` — inline buttons, callback data format, truncation
- `_edit_field_keyboard()` — all 6 fields, cancel button

#### Module: conversations.py (`app/bot/conversations.py`) — parse_deadline
- Keyword shortcuts: today, tomorrow, next week
- Relative: in N days/hours/weeks
- Weekday names: all 7, next-week logic for same-day
- Absolute formats: ISO, slash d/m/y, dot d.m.y, dash d-m-y, US m/d/y
- Error paths: garbage input, empty string, hints in error message
- Wizard inline keyboards: _category_inline, _priority_inline, _skip_inline

#### Module: handlers.py (`app/bot/handlers.py`) — utility layer
- `_delete()` — None input, success, exception swallowing
- `_safe_edit()` — success, "not modified" swallowed, "can't be edited" swallowed, other BadRequest re-raised
- State constants: unique values, EDIT_FIELDS completeness
- `_TIMEZONE_MAP`, `_FILTER_MAP`: content and format validation

#### Module: reminders.py (`app/bot/reminders.py`)
- `create_scheduler()` — returns AsyncIOScheduler, 2 jobs with correct trigger types
- `check_deadlines()` — empty tasks, message count per task, mark_reminded called, chat_id, failure resilience
- `send_daily_summaries()` — no users, zero-task skip, DB error, per-user error, invalid timezone

### Test Deliverables

1. **Test Strategy & Test Plan Document** — This document defining testing approach
2. **Test Cases Document** — Detailed test cases with expected results
3. **Test Execution Results** — Individual test run outputs and logs
4. **Test Report** — Summary of results, coverage, and findings
5. **Bug Report** — Documented issues found during testing with reproduction steps

### Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| Database state inconsistency during tests | Medium | High | Use database fixtures and transactions to isolate tests |
| API rate limiting during integration tests | Medium | Medium | Mock external API calls, test with limited requests |
| Async test timing issues | Medium | Medium | Use pytest-asyncio with proper fixtures and timeouts |
| Test environment divergence from production | Low | High | Keep test environment configuration synchronized with production |
| Incomplete code coverage | Medium | Medium | Generate coverage reports and add tests for uncovered branches |
| Telegram API changes | Low | High | Test against current API version, monitor for deprecations |
| Data inconsistency between databases | Low | Medium | Use schema versioning and migration testing |
| Time-dependent test failures | Medium | Medium | Mock time-dependent functions, use fixed dates in tests |

### Success Criteria

- ✓ All unit tests pass (100% pass rate)
- ✓ All integration tests pass (100% pass rate)
- ✓ All system tests on deployed server pass
- ✓ Code coverage ≥ 80% for core modules
- ✓ No critical severity bugs remaining
- ✓ All test deliverables completed and documented
- ✓ Test execution completed by March 23, 2026
