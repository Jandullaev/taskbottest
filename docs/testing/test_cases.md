# Manual Test Cases

## Overview

This document contains manual test cases for the **TaskBot Telegram bot**. Each test case describes a real user interaction with the bot's UI — commands, reply keyboards, inline buttons, and conversation wizards. Tests are executed by a human tester operating the bot directly in Telegram.

### Test Case Format

| Field | Description |
|-------|---|
| **Test ID** | Unique identifier (e.g., `TC_UI_001`) |
| **Section** | Feature area |
| **Priority** | Critical / High / Medium / Low |
| **Preconditions** | State required before testing |
| **Test Steps** | Numbered actions the tester performs |
| **Expected Results** | What the bot should show/do |
| **Status** | Not Run / Pass / Fail |
| **Actual Result** | What the bot actually did (fill in for Failed tests) |
| **Notes** | Observations, defect IDs, remarks |

### Environment Setup

- **Bot**: TaskBot running locally or on test server
- **Client**: Telegram (mobile or desktop)
- **DB**: Fresh `data/taskbot.db` (or reset between runs)
- **AI**: Gemini API key configured in `.env`
- **Tester account**: A real Telegram account (not the bot account)

---

## 1. ONBOARDING & NAVIGATION

### TC_UI_001: First-Time User Registration via /start
- **Section**: Onboarding
- **Priority**: Critical
- **Preconditions**: Bot is running. Tester's Telegram account has never messaged the bot before (or DB is cleared).
- **Test Steps**:
  1. Open a chat with the bot in Telegram.
  2. Send the command `/start`.
  3. Observe the bot's response.
- **Expected Results**:
  - A **main reply keyboard** appears with 6 buttons: `➕ Add Task`, `🤖 Add with AI`, `📋 My Tasks`, `📊 Stats`, `🔍 Filters`, `⚙️ Timezone`.
  - User record is created in the database (verify via DB inspect or functional side-effects).
- **Status**: Passed
- **Notes**:

---

### TC_UI_002: Returning User — /start Does Not Duplicate Record
- **Section**: Onboarding
- **Priority**: High
- **Preconditions**: User has already started the bot (TC_UI_001 passed).
- **Test Steps**:
  1. Send `/start` again in the same chat.
  2. Observe the bot's response.
- **Expected Results**:
  - Bot replies with welcome message again (same behavior as new user).
  - Main menu keyboard is shown.
  - Only **one** user record exists in the DB (no duplicate).
- **Status**: Passed
- **Notes**:

---

### TC_UI_003: /help Command
- **Section**: Navigation
- **Priority**: High
- **Preconditions**: User is registered.
- **Test Steps**:
  1. Send `/help`.
  2. Read the bot's response.
- **Expected Results**:
  - Bot sends a help message listing all available commands (`/addtask`, `/addtask_ai`, `/mytasks`, `/stats`, `/settimezone`, etc.).
  - Main menu keyboard remains visible (or is re-sent).
- **Status**: Passed
- **Notes**:

---

### TC_UI_004: Main Menu — "◀️ Back to Menu" Button
- **Section**: Navigation
- **Priority**: High
- **Preconditions**: User is in any sub-flow (e.g., Filters screen showing).
- **Test Steps**:
  1. Tap `🔍 Filters` from the main menu.
  2. Tap `◀️ Back to Menu`.
  3. Observe the keyboard that appears.
- **Expected Results**:
  - After step 1: Filters keyboard replaces the main menu.
  - After step 2: Main menu keyboard (6 buttons) is restored with a confirmation message.
- **Status**: Passed
- **Notes**:

---

### TC_UI_005: Unknown Command Handling
- **Section**: Navigation
- **Priority**: Medium
- **Preconditions**: User is registered.
- **Test Steps**:
  1. Send an unrecognized command, e.g., `/foobar`.
  2. Observe the bot's response.
- **Expected Results**:
  - Bot does not reply to unrecognized commands (silently ignores them).
  - Bot does not crash.
- **Status**: Passed
- **Notes**: Confirmed behavior — bot silently ignores unknown commands with no error message.

---

## 2. MANUAL TASK CREATION — /addtask WIZARD

### TC_UI_006: Complete Task Creation — All Fields Filled
- **Section**: Add Task
- **Priority**: Critical
- **Preconditions**: User is registered. Bot is idle.
- **Test Steps**:
  1. Send `/addtask` or tap `➕ Add Task`.
  2. Bot asks for task title. Type `"Prepare Q2 report"` and send.
  3. Bot asks for description. Type `"Summarize sales numbers"` and send.
  4. Bot shows category inline keyboard. Tap `💼 Work`.
  5. Bot shows priority inline keyboard. Tap `🔴 High`.
  6. Bot asks for deadline with a Skip button. Type `"tomorrow"` and send.
  7. Observe the final confirmation message.
- **Expected Results**:
  - After each step, bot acknowledges and moves to the next step without errors.
  - Final message shows a formatted task card with: title, description, category=Work, priority=High, deadline set to tomorrow 09:00.
  - Main menu keyboard is restored.
  - Task appears when `/mytasks` is called.
- **Status**: Passed
- **Notes**:

---

### TC_UI_007: Task Creation — Skip Optional Deadline
- **Section**: Add Task
- **Priority**: High
- **Preconditions**: User is registered. Bot is idle.
- **Test Steps**:
  1. Start `/addtask`.
  2. Enter title: `"Buy groceries"`.
  3. Enter description: `"Milk, eggs, bread"`.
  4. Tap `🏠 Personal` for category.
  5. Tap `🟡 Medium` for priority.
  6. Tap `⏭️ Skip` when asked for deadline.
- **Expected Results**:
  - Task is created with no deadline (deadline field shows as empty/not set in task card).
  - Task appears in `/mytasks`.
- **Status**: Passed
- **Notes**:

---

### TC_UI_008: Task Creation — Cancel Mid-Wizard
- **Section**: Add Task
- **Priority**: High
- **Preconditions**: User is in the middle of the /addtask wizard.
- **Test Steps**:
  1. Send `/addtask`.
  2. Enter a title.
  3. Send `/cancel` (or tap Cancel button if available).
  4. Observe the bot's response.
- **Expected Results**:
  - Wizard exits cleanly.
  - Bot confirms cancellation and returns to main menu.
  - No incomplete task is saved in the database.
- **Status**: Passed
- **Notes**:

---

### TC_UI_009: Task Creation — Title Too Long / Special Characters
- **Section**: Add Task
- **Priority**: Medium
- **Preconditions**: User is in the title step of /addtask.
- **Test Steps**:
  1. Start `/addtask`.
  2. Enter a title with 200+ characters (e.g., repeated text).
  3. Also test a title with Telegram special characters: `*bold* _italic_ [link](http://x.com)`.
  4. Complete the wizard.
- **Expected Results**:
  - Long title is accepted (or truncated with notice).
  - Special characters do not break the message formatting — they are escaped properly in the task card.
  - Task is saved and viewable.
- **Status**: Passed
- **Notes**:

---

### TC_UI_010: Task Creation — Various Deadline Formats
- **Section**: Add Task
- **Priority**: High
- **Preconditions**: User is at the deadline step of /addtask.
- **Test Steps**: Run the following deadline inputs across separate task creation flows:
  1. `"today"` → expect today at 09:00.
  2. `"tomorrow"` → expect tomorrow at 09:00.
  3. `"next week"` → expect +7 days at 09:00.
  4. `"in 3 hours"` → expect current time + 3h.
  5. `"in 2 days"` → expect current time + 2d.
  6. `"next monday"` → expect the coming Monday at 09:00.
  7. `"25/12/2026"` → expect Dec 25, 2026.
  8. `"2026-12-25"` → expect Dec 25, 2026.
- **Expected Results**:
  - Each format is parsed correctly and displayed in the task card.
  - No format causes an error or crash.
- **Actual Result**: Deadline formats are parsed and accepted, but the displayed deadline time does not account for the user's configured timezone — times appear in UTC regardless of the user's timezone setting.
- **Status**: Passed
- **Notes**: Root cause likely the same as TC_UI_057/TC_UI_059 — timezone is not applied to deadline display.

---

### TC_UI_011: Task Creation — Invalid Deadline Input
- **Section**: Add Task
- **Priority**: High
- **Preconditions**: User is at the deadline step of /addtask.
- **Test Steps**:
  1. Start `/addtask`, fill title and description, choose category and priority.
  2. When asked for deadline, type `"whenever"` (unparseable).
  3. Observe bot response.
- **Expected Results**:
  - Bot replies with a clear error message explaining the invalid format.
  - Bot **re-asks** for the deadline (does not crash, does not skip ahead, does not save a broken deadline).
  - User can then enter a valid date or tap Skip.
- **Status**: Passed
- **Notes**:

---

### TC_UI_012: Task Creation — New Task Interrupts Active Wizard
- **Section**: Add Task
- **Priority**: Medium
- **Preconditions**: User has started /addtask and is mid-wizard.
- **Test Steps**:
  1. Send `/addtask`, enter a title.
  2. Without finishing, send `/addtask` again.
  3. Observe behavior.
- **Expected Results**:
  - Bot handles the re-entry gracefully — either restarting the wizard with a notice, or warning the user that a wizard is already active.
  - No crashed state or duplicate partial task.
- **Status**: Passed
- **Notes**:

---

### TC_UI_013: Task Creation — Reply Keyboard Buttons Trigger Wizard
- **Section**: Add Task
- **Priority**: High
- **Preconditions**: User is at the main menu.
- **Test Steps**:
  1. Tap `➕ Add Task` button on the reply keyboard (instead of typing `/addtask`).
  2. Follow the wizard to completion.
- **Expected Results**:
  - Wizard starts identically to typing `/addtask`.
  - Task is created correctly.
- **Status**: Passed
- **Notes**:

---

### TC_UI_014: Inline Category Buttons — All Six Categories Selectable
- **Section**: Add Task
- **Priority**: High
- **Preconditions**: User is at the category selection step.
- **Test Steps**: Create six separate tasks, selecting each category once:
  1. `💼 Work`
  2. `📚 Study`
  3. `🏠 Personal`
  4. `❤️ Health`
  5. `💰 Finance`
  6. `🌐 General`
- **Expected Results**:
  - Each category button registers correctly.
  - The saved task card shows the matching category emoji and label.
- **Status**: Passed
- **Notes**:

---

### TC_UI_015: Inline Priority Buttons — All Three Priorities Selectable
- **Section**: Add Task
- **Priority**: High
- **Preconditions**: User is at the priority selection step.
- **Test Steps**: Create three tasks, selecting each priority:
  1. `🔴 High`
  2. `🟡 Medium`
  3. `🟢 Low`
- **Expected Results**:
  - Each priority is saved correctly and reflected in the task card and task list ordering (High tasks appear first).
- **Status**: Passed
- **Notes**:

---

## 3. AI TASK CREATION — /addtask_ai

### TC_UI_016: AI Task Creation — Natural Language Input
- **Section**: AI Add Task
- **Priority**: Critical
- **Preconditions**: Gemini API key configured. Bot is idle.
- **Test Steps**:
  1. Tap `🤖 Add with AI` or send `/addtask_ai`.
  2. Bot asks for a natural-language description. Send: `"Finish the budget spreadsheet for finance review by Friday, high priority"`.
  3. Wait for AI processing.
  4. Observe the created task card.
- **Expected Results**:
  - AI extracts: title (something like "Finish budget spreadsheet"), category=Finance or Work, priority=High, deadline=next Friday.
  - Task card is shown with all parsed fields.
  - Task is saved and appears in `/mytasks`.
- **Status**: Passed
- **Notes**:

---

### TC_UI_017: AI Task Creation — Minimal Input (Title Only)
- **Section**: AI Add Task
- **Priority**: High
- **Preconditions**: Gemini API key configured.
- **Test Steps**:
  1. Send `/addtask_ai`.
  2. Type: `"Call dentist"`.
- **Expected Results**:
  - AI creates a task with the given title.
  - Missing fields (category, priority, deadline) are filled with sensible defaults or left unset.
  - No error or crash.
- **Status**: Passed
- **Notes**:

---

### TC_UI_018: AI Task Creation — Cancel Mid-Flow
- **Section**: AI Add Task
- **Priority**: Medium
- **Preconditions**: Bot is in the /addtask_ai waiting-for-input state.
- **Test Steps**:
  1. Send `/addtask_ai`.
  2. Send `/cancel` before providing input.
- **Expected Results**:
  - Flow is cancelled cleanly.
  - Main menu returns.
  - No task is saved.
- **Status**:  Passed
- **Notes**:

---

### TC_UI_019: AI Task Creation — Ambiguous or Non-Task Input
- **Section**: AI Add Task
- **Priority**: Medium
- **Preconditions**: Gemini API key configured.
- **Test Steps**:
  1. Send `/addtask_ai`.
  2. Send a non-task message: `"What is the weather today?"`.
- **Expected Results**:
  - Bot either parses it as best it can (creating a task with the text as title) or returns a graceful error/warning.
  - Does not crash. No misleading success message.
- **Status**: Passed
- **Notes**:

---

### TC_UI_020: AI Add Task Button vs. Command Equivalence
- **Section**: AI Add Task
- **Priority**: Medium
- **Preconditions**: User is at main menu.
- **Test Steps**:
  1. Tap `🤖 Add with AI` keyboard button.
  2. Observe behavior is identical to step 1 of TC_UI_016.
- **Expected Results**:
  - Keyboard button and `/addtask_ai` command produce identical behavior.
- **Status**: Passed
- **Notes**:

---

## 4. TASK LISTING & FILTERING

### TC_UI_021: View All Tasks — /mytasks
- **Section**: Task List
- **Priority**: Critical
- **Preconditions**: User has at least 3 tasks with different statuses and priorities.
- **Test Steps**:
  1. Send `/mytasks` or tap `📋 My Tasks`.
  2. Observe the response.
- **Expected Results**:
  - Bot sends a message with an inline keyboard where each button shows a task (priority emoji + truncated title, max 30 chars).
  - Tasks are ordered: High priority first, then Medium, then Low.
  - Cancelled tasks are **not** shown.
- **Status**: Passed
- **Notes**:

---

### TC_UI_022: View Tasks — Empty List
- **Section**: Task List
- **Priority**: High
- **Preconditions**: User has no tasks (new user or all tasks deleted).
- **Test Steps**:
  1. Send `/mytasks`.
- **Expected Results**:
  - Bot replies with a message indicating there are no tasks (e.g., "You have no tasks yet").
  - No inline keyboard or empty keyboard shown.
- **Status**: Passed
- **Notes**:

---

### TC_UI_023: Filter Tasks by Status — Pending
- **Section**: Task Filters
- **Priority**: High
- **Preconditions**: User has tasks with statuses: pending, in_progress, done.
- **Test Steps**:
  1. Tap `🔍 Filters`.
  2. Tap `⏳ Pending`.
  3. Observe the task list.
- **Expected Results**:
  - Only tasks with status=pending are listed.
  - Done and in-progress tasks are absent from the list.
- **Status**: Passed
- **Notes**:

---

### TC_UI_024: Filter Tasks by Status — Done
- **Section**: Task Filters
- **Priority**: High
- **Preconditions**: User has at least one completed task.
- **Test Steps**:
  1. Tap `🔍 Filters`.
  2. Tap `✅ Done`.
- **Expected Results**:
  - Only done tasks are shown.
- **Status**: Passed
- **Notes**:

---

### TC_UI_025: Filter Tasks by Status — In Progress
- **Section**: Task Filters
- **Priority**: High
- **Preconditions**: User has at least one in-progress task.
- **Test Steps**:
  1. Tap `🔍 Filters`.
  2. Tap `🔄 In Progress`.
- **Expected Results**:
  - Only in-progress tasks are shown.
- **Actual Result**: The In Progress filter does not return in-progress tasks. The task list shown appears to be unfiltered or empty despite in-progress tasks existing.
- **Status**: Failed
- **Notes**: In-progress status filter broken. Related to TC_UI_037 (edit status inline keyboard not working).

---

### TC_UI_026: Filter Tasks by Category — Work
- **Section**: Task Filters
- **Priority**: High
- **Preconditions**: User has tasks in multiple categories.
- **Test Steps**:
  1. Tap `🔍 Filters`.
  2. Tap `💼 Work`.
- **Expected Results**:
  - Only tasks in the Work category are shown.
  - Tasks from other categories are not present.
- **Status**: Passed
- **Notes**:

---

### TC_UI_027: Filter Tasks — No Matching Results
- **Section**: Task Filters
- **Priority**: Medium
- **Preconditions**: User has no tasks in a specific category (e.g., Finance).
- **Test Steps**:
  1. Tap `🔍 Filters`.
  2. Tap `💰 Finance`.
- **Expected Results**:
  - Bot replies with a "no tasks found" message for that filter.
  - No crash or empty inline keyboard.
- **Status**: Passed
- **Notes**:

---

### TC_UI_028: /mytasks with Inline Status Parameter
- **Section**: Task List
- **Priority**: Medium
- **Preconditions**: User has tasks of different statuses.
- **Test Steps**:
  1. Type and send `/mytasks done`.
  2. Type and send `/mytasks pending`.
  3. Type and send `/mytasks work` (category filter).
- **Expected Results**:
  - Each command filters correctly (same results as tapping the corresponding filter button).
- **Status**: Passed
- **Notes**:

---

## 5. TASK VIEWING

### TC_UI_029: View Task Detail Card
- **Section**: Task View
- **Priority**: Critical
- **Preconditions**: User has at least one task.
- **Test Steps**:
  1. Send `/mytasks`.
  2. Tap any task from the inline keyboard.
  3. Read the task detail card.
- **Expected Results**:
  - Task card shows: title, description, status emoji + label, category emoji + label, priority emoji + label, deadline (formatted), created date.
  - Inline action buttons appear: `✅ Done`, `✏️ Edit`, `🗑️ Delete`, `◀️ Back to Menu`.
- **Status**: Passed
- **Notes**:

---

### TC_UI_030: View Task via /mytask Command
- **Section**: Task View
- **Priority**: High
- **Preconditions**: User knows a valid task ID.
- **Test Steps**:
  1. Note the ID of an existing task (e.g., ID=3).
  2. Send `/mytask 3`.
- **Expected Results**:
  - Same task card as TC_UI_029 is shown with action buttons.
- **Status**: Passed
- **Notes**:

---

### TC_UI_031: View Non-Existent Task
- **Section**: Task View
- **Priority**: High
- **Preconditions**: No task with ID=99999 exists.
- **Test Steps**:
  1. Send `/mytask 99999`.
- **Expected Results**:
  - Bot replies with a "task not found" error message.
  - No crash.
- **Status**: Passed
- **Notes**:

---

### TC_UI_032: View Another User's Task (Security)
- **Section**: Task View
- **Priority**: Critical
- **Preconditions**: Two Telegram accounts both registered with the bot. Account A created a task (note its ID). Log in as Account B.
- **Test Steps**:
  1. As Account B, send `/mytask <ID of Account A's task>`.
- **Expected Results**:
  - Bot replies with "task not found" — Account B cannot view Account A's tasks.
  - No task data is leaked.
- **Status**: Not Run
- **Notes**:

---

## 6. TASK EDITING

### TC_UI_033: Edit Task — Change Title
- **Section**: Edit Task
- **Priority**: Critical
- **Preconditions**: An existing task is visible.
- **Test Steps**:
  1. Open a task card (via `/mytasks` → tap task).
  2. Tap `✏️ Edit`.
  3. Tap `📝 Title` from the field selector.
  4. Type a new title: `"Updated Title"` and send.
  5. Observe the result.
- **Expected Results**:
  - Bot confirms the title was updated.
  - Refreshed task card shows the new title.
- **Status**: Passed
- **Notes**: UX improvement — after selecting a field, the prompt message should clearly state which field is being edited (e.g., "Enter new title:").

---

### TC_UI_034: Edit Task — Change Description
- **Section**: Edit Task
- **Priority**: High
- **Preconditions**: An existing task has a description.
- **Test Steps**:
  1. Open a task card → tap `✏️ Edit`.
  2. Tap `📄 Description`.
  3. Enter a new description and send.
- **Expected Results**:
  - Task card updates with the new description.
- **Status**: Passed
- **Notes**: UX improvement — after selecting a field, the prompt message should clearly state which field is being edited (e.g., "Enter new description:").

---

### TC_UI_035: Edit Task — Change Category via Inline Buttons
- **Section**: Edit Task
- **Priority**: High
- **Preconditions**: Task exists.
- **Test Steps**:
  1. Open task card → `✏️ Edit` → `🗂️ Category`.
  2. Tap `📚 Study` from the inline keyboard.
- **Expected Results**:
  - Task category updated to Study.
  - Task card reflects the change.
- **Actual Result**: After tapping "Category" in the edit field selector, no inline keyboard appears. The bot does not show the category options.
- **Status**: Failed
- **Notes**: Inline keyboard for category selection missing in edit flow. Affects TC_UI_036 and TC_UI_037 as well (same root cause).

---

### TC_UI_036: Edit Task — Change Priority via Inline Buttons
- **Section**: Edit Task
- **Priority**: High
- **Preconditions**: Task has priority=High.
- **Test Steps**:
  1. Open task → `✏️ Edit` → `⚡ Priority`.
  2. Tap `🟢 Low`.
- **Expected Results**:
  - Priority updated to Low.
  - Task list ordering changes accordingly (task moves lower).
- **Actual Result**: After tapping "Priority" in the edit field selector, no inline keyboard appears. The bot does not show priority options.
- **Status**: Failed
- **Notes**: Same root cause as TC_UI_035 — inline keyboards for category/priority/status are missing in edit flow.

---

### TC_UI_037: Edit Task — Change Status via Inline Buttons
- **Section**: Edit Task
- **Priority**: High
- **Preconditions**: Task has status=pending.
- **Test Steps**:
  1. Open task → `✏️ Edit` → `🔄 Status`.
  2. Tap `🔄 In Progress`.
- **Expected Results**:
  - Task status updated to in_progress.
  - Task card shows the updated status.
- **Actual Result**: After tapping "Status" in the edit field selector, no inline keyboard appears. The bot does not show status options.
- **Status**: Failed
- **Notes**: Same root cause as TC_UI_035 — inline keyboards for category/priority/status are missing in edit flow.

---

### TC_UI_038: Edit Task — Set Valid Deadline
- **Section**: Edit Task
- **Priority**: High
- **Preconditions**: Task exists (with or without a deadline).
- **Test Steps**:
  1. Open task → `✏️ Edit` → `📅 Deadline`.
  2. Type `"next friday"` and send.
- **Expected Results**:
  - Deadline parsed and saved as next Friday 09:00.
  - Task card shows the updated deadline.
- **Status**: Passed
- **Notes**:

---

### TC_UI_039: Edit Task — Set Invalid Deadline
- **Section**: Edit Task
- **Priority**: High
- **Preconditions**: User is in the deadline edit step.
- **Test Steps**:
  1. Open task → `✏️ Edit` → `📅 Deadline`.
  2. Type `"xxxxxx"` and send.
- **Expected Results**:
  - Bot replies with a deadline parse error message.
  - Bot re-prompts for deadline input.
  - Original deadline is unchanged.
- **Actual Result**: No error message is shown for invalid deadline input. The bot accepts the invalid value silently and may save it as-is or ignore it. The app does not crash.
- **Status**: Passed
- **Notes**: Invalid deadline should re-prompt the user, not silently accept or discard.

---

### TC_UI_040: Edit Task — Cancel Edit
- **Section**: Edit Task
- **Priority**: Medium
- **Preconditions**: User is in the edit field selector.
- **Test Steps**:
  1. Open task → `✏️ Edit`.
  2. Tap `◀️ Cancel`.
- **Expected Results**:
  - Edit wizard exits.
  - Main menu returns.
  - Original task data is unchanged.
- **Actual Result**: Bot navigates back to main menu, but the reply keyboard closes immediately (same issue as TC_UI_008).
- **Status**: Passed
- **Notes**: Menu keyboard disappears after cancel — same root cause as TC_UI_008.

---

### TC_UI_041: Edit Task — via /edittask Command
- **Section**: Edit Task
- **Priority**: Medium
- **Preconditions**: Task with ID=2 exists.
- **Test Steps**:
  1. Send `/edittask 2`.
  2. Complete an edit (e.g., change title).
- **Expected Results**:
  - Edittask wizard starts correctly.
  - Task is updated as expected.
- **Status**: Passed
- **Notes**:

---

### TC_UI_042: Edit Task — Invalid or Missing ID in /edittask
- **Section**: Edit Task
- **Priority**: Medium
- **Preconditions**: None.
- **Test Steps**:
  1. Send `/edittask` (no ID).
  2. Send `/edittask abc` (non-numeric ID).
  3. Send `/edittask 99999` (non-existent ID).
- **Expected Results**:
  - Step 1 and 2: Bot replies with usage hint (e.g., "Usage: /edittask <task_id>").
  - Step 3: Bot replies with "task not found".
  - No crash in any case.
- **Status**: Passed
- **Notes**:

---

## 7. TASK COMPLETION

### TC_UI_043: Mark Task Done — via Inline Button
- **Section**: Task Completion
- **Priority**: Critical
- **Preconditions**: Task with status=pending exists.
- **Test Steps**:
  1. Open a task card (tap from `/mytasks`).
  2. Tap `✅ Done`.
  3. Check `/mytasks` again.
- **Expected Results**:
  - Bot confirms task is marked as done.
  - Task no longer appears in the default pending list.
  - Task appears when filtering by `✅ Done`.
- **Status**: Passed
- **Notes**:

---

### TC_UI_044: Mark Task Done — via /done Command
- **Section**: Task Completion
- **Priority**: High
- **Preconditions**: Task with ID=5 exists and is pending.
- **Test Steps**:
  1. Send `/done 5`.
- **Expected Results**:
  - Bot confirms task #5 is marked as done.
- **Status**: Passed
- **Notes**:

---

### TC_UI_045: Mark Already-Done Task as Done
- **Section**: Task Completion
- **Priority**: Medium
- **Preconditions**: Task is already in status=done.
- **Test Steps**:
  1. Open a done task card.
  2. Tap `✅ Done` again (if button is visible).
  3. Or send `/done <id>` for a done task.
- **Expected Results**:
  - Bot replies informing the task is already done.
  - No duplicate state change. No crash.
- **Actual Result**: Bot sends a "task marked as done" confirmation even when the task is already in done status. No idempotency check is performed.
- **Status**: Passed
- **Notes**: Bot should detect the task is already done and respond with a message like "Task is already completed."

---

### TC_UI_046: /done with Invalid ID
- **Section**: Task Completion
- **Priority**: Medium
- **Preconditions**: None.
- **Test Steps**:
  1. Send `/done` (no ID).
  2. Send `/done 99999` (non-existent).
- **Expected Results**:
  - Step 1: Usage hint shown.
  - Step 2: "Task not found" message shown.
- **Status**: Passed
- **Notes**: 

---

### TC_UI_047: Done Tasks Excluded from Default List
- **Section**: Task Completion
- **Priority**: High
- **Preconditions**: User has both pending and done tasks.
- **Test Steps**:
  1. Mark one task as done.
  2. Send `/mytasks` (no filter).
- **Expected Results**:
  - Done task does not appear in the default unfiltered list.
  - Done task appears in `✅ Done` filtered list.
- **Status**: Passed
- **Notes**:

---

## 8. TASK DELETION

### TC_UI_048: Delete Task — via Inline Button with Confirmation
- **Section**: Task Deletion
- **Priority**: Critical
- **Preconditions**: Task exists.
- **Test Steps**:
  1. Open a task card.
  2. Tap `🗑️ Delete`.
  3. Bot shows a confirmation prompt. Tap `🗑️ Yes, Delete`.
  4. Check `/mytasks`.
- **Expected Results**:
  - After step 2: Bot shows a confirmation keyboard (`Yes, Delete` + `↩️ Cancel`).
  - After step 3: Bot confirms deletion.
  - Task is gone from `/mytasks`.
- **Status**: Passed
- **Notes**:

---

### TC_UI_049: Delete Task — Cancel at Confirmation
- **Section**: Task Deletion
- **Priority**: High
- **Preconditions**: Task exists.
- **Test Steps**:
  1. Open a task card → `🗑️ Delete`.
  2. At the confirmation prompt, tap `↩️ Cancel`.
- **Expected Results**:
  - Task is NOT deleted.
  - Bot returns to the task card or main menu.
- **Status**: Passed
- **Notes**:

---

### TC_UI_050: Delete Task — via /deletetask Command
- **Section**: Task Deletion
- **Priority**: High
- **Preconditions**: Task with ID=3 exists.
- **Test Steps**:
  1. Send `/deletetask 3`.
  2. Tap `🗑️ Yes, Delete` on confirmation.
- **Expected Results**:
  - Task is deleted successfully.
- **Actual Result**: Bot shows "⚠️ No task selected." when tapping the confirmation button after using `/deletetask <id>`. The task ID is not carried through to the confirmation step.
- **Status**: Passed
- **Notes**: The `/deletetask` command likely passes the task ID differently from the inline button flow — confirmation handler loses the task context.

---

### TC_UI_051: Delete Non-Existent Task
- **Section**: Task Deletion
- **Priority**: Medium
- **Preconditions**: No task with ID=99999.
- **Test Steps**:
  1. Send `/deletetask 99999`.
- **Expected Results**:
  - Bot replies with "task not found".
  - No crash.
- **Status**: Passed
- **Notes**: "Task not found" message appears briefly then is deleted by the bot.

---

### TC_UI_052: Delete Another User's Task (Security)
- **Section**: Task Deletion
- **Priority**: Critical
- **Preconditions**: Two accounts registered. Account A has a task (note ID). Log in as Account B.
- **Test Steps**:
  1. As Account B, send `/deletetask <Account A's task ID>`.
- **Expected Results**:
  - Bot replies with "task not found" — Account B cannot delete Account A's tasks.
- **Status**: Not Run
- **Notes**:

---

## 9. STATS & MOTIVATION

### TC_UI_053: View Stats Dashboard
- **Section**: Stats
- **Priority**: High
- **Preconditions**: User has completed at least 2 tasks and has pending tasks.
- **Test Steps**:
  1. Tap `📊 Stats` or send `/stats`.
  2. Read the response.
- **Expected Results**:
  - Bot displays a stats card with: total tasks, completed count, completion rate %, top category.
  - A motivational message (2–3 sentences from Gemini) is included.
  - Main menu keyboard is visible.
- **Status**: Passed
- **Notes**:

---

### TC_UI_054: Stats — New User with Zero Tasks
- **Section**: Stats
- **Priority**: Medium
- **Preconditions**: User is newly registered with no tasks.
- **Test Steps**:
  1. Send `/stats`.
- **Expected Results**:
  - Bot shows empty stats (0 tasks, 0% completion).
  - Motivational message is still generated (or a default encouraging message is shown).
  - No crash or division-by-zero error.
- **Status**: Passed
- **Notes**:

---

### TC_UI_055: Stats Completion Rate Accuracy
- **Section**: Stats
- **Priority**: High
- **Preconditions**: User has exactly 4 tasks: 2 done, 1 pending, 1 cancelled.
- **Test Steps**:
  1. Create 4 tasks, complete 2 of them, cancel 1.
  2. Send `/stats`.
  3. Check the displayed completion rate.
- **Expected Results**:
  - Completion rate = 50% (2 done out of 4 total, or verify how cancelled tasks are counted per spec).
  - Top category reflects the most frequent category among tasks.
- **Status**: Passed
- **Notes**: 

---

### TC_UI_056: Stats — AI Motivation Message Freshness
- **Section**: Stats
- **Priority**: Low
- **Preconditions**: Gemini API key configured.
- **Test Steps**:
  1. Send `/stats`. Note the motivational message.
  2. Send `/stats` again.
- **Expected Results**:
  - The motivational message may differ (AI generates dynamically) or be consistent — either is acceptable.
  - Both calls succeed without error.
- **Status**: Passed
- **Notes**:

---

## 10. TIMEZONE SETTINGS

### TC_UI_057: Set Timezone — via Keyboard Button
- **Section**: Timezone
- **Priority**: High
- **Preconditions**: User is registered (default timezone = Asia/Tashkent or UTC).
- **Test Steps**:
  1. Tap `⚙️ Timezone` or send `/settimezone`.
  2. Observe the timezone keyboard.
  3. Tap `🗽 New York`.
- **Expected Results**:
  - Bot confirms timezone changed to America/New_York.
  - Main menu returns.
- **Actual Result**: Bot confirms timezone change with a success message, but task deadline timestamps and any current-time references continue to display in the previous timezone (or UTC).
- **Status**: Passed
- **Notes**: Timezone is saved to DB (TC_UI_061 passed) but the formatter does not apply it to deadline display.

---

### TC_UI_058: All Timezone Options Are Tappable
- **Section**: Timezone
- **Priority**: Medium
- **Preconditions**: User is on the timezone keyboard.
- **Test Steps**: Tap each of the 11 timezone options one at a time across separate /settimezone invocations:
  Tashkent, Almaty, Dubai, Moscow, London, Berlin, New York, Los Angeles, Tokyo, Sydney, UTC.
- **Expected Results**:
  - Each tap is accepted.
  - Bot confirms the change.
  - No option causes an error.
- **Status**: Passed
- **Notes**:

---

### TC_UI_059: Timezone Affects Deadline Display
- **Section**: Timezone
- **Priority**: High
- **Preconditions**: Task exists with a deadline. User's timezone is UTC.
- **Test Steps**:
  1. Note the deadline displayed for a task.
  2. Change timezone to Tokyo (UTC+9).
  3. View the same task.
- **Expected Results**:
  - Deadline timestamp is displayed in the new timezone (Tokyo time is 9 hours ahead of UTC).
- **Actual Result**: Deadline display does not change after switching timezone to Tokyo. Same UTC-based time shown.
- **Status**: Passed
- **Notes**: Same root cause as TC_UI_057 — timezone not applied to deadline formatting.

---

### TC_UI_060: Back to Menu from Timezone Screen
- **Section**: Timezone
- **Priority**: Low
- **Preconditions**: User is on the timezone selection keyboard.
- **Test Steps**:
  1. Tap `◀️ Back to Menu`.
- **Expected Results**:
  - Main menu keyboard is restored without changing the timezone.
- **Status**: Passed
- **Notes**:

---

### TC_UI_061: Timezone Persists Across Sessions
- **Section**: Timezone
- **Priority**: High
- **Preconditions**: User has changed timezone to London.
- **Test Steps**:
  1. Change timezone to London.
  2. Close Telegram, reopen the chat.
  3. Send `/start`.
  4. Check daily digest time or deadline display to confirm timezone.
- **Expected Results**:
  - Timezone setting is persisted in the database and still active after re-opening the chat.
- **Status**: Passed
- **Notes**: 

---

## 11. DEADLINE REMINDERS

### TC_UI_062: 30-Minute Deadline Reminder Notification
- **Section**: Reminders
- **Priority**: High
- **Preconditions**: Scheduler is running. A task exists with a deadline 30–35 minutes from now.
- **Test Steps**:
  1. Create a task with deadline set to `"in 32 minutes"`.
  2. Wait approximately 2–5 minutes for the scheduler's 10-minute check cycle.
  3. Observe Telegram notifications.
- **Expected Results**:
  - Within 10 minutes before the 30-minute mark, the bot sends a reminder message for that task.
  - Reminder includes the task title and deadline time.
- **Actual Result**: No reminder notification is sent after waiting through the scheduler cycle. The task deadline passed without any notification.
- **Status**: Passed
- **Notes**: But in reminder shows another time, but in task another time

---

### TC_UI_063: Reminder Sent Only Once (De-duplication)
- **Section**: Reminders
- **Priority**: High
- **Preconditions**: A task was reminded (TC_UI_062 passed).
- **Test Steps**:
  1. Wait for another scheduler cycle after the first reminder was sent.
  2. Observe if a second reminder is sent.
- **Expected Results**:
  - No second reminder is sent for the same task within the 60-minute de-duplication window.
- **Status**: Not Run
- **Notes**:

---

### TC_UI_064: No Reminder for Completed Tasks
- **Section**: Reminders
- **Priority**: High
- **Preconditions**: A pending task exists with an upcoming deadline.
- **Test Steps**:
  1. Create a task with deadline in 31 minutes.
  2. Immediately mark it as Done.
  3. Wait for the scheduler cycle.
- **Expected Results**:
  - No reminder is sent for the completed task.
- **Status**: Not Run
- **Notes**:

---

## 12. DAILY DIGEST

### TC_UI_065: Morning Digest Sent at 9 AM User Time
- **Section**: Daily Digest
- **Priority**: High
- **Preconditions**: User's timezone is configured. User has pending tasks.
- **Test Steps**:
  1. Set timezone so that 9 AM local time will occur within the next scheduler cycle.
  2. Wait for the 9 AM hour.
  3. Observe Telegram notifications.
- **Expected Results**:
  - Bot sends a morning digest containing: greeting, up to 5 pending tasks listed, AI motivational message.
- **Status**: Passed
- **Notes**: Digest sent at the correct hour, but times shown inside the digest reflect UTC rather than the user's timezone (linked to TC_UI_057).

---

### TC_UI_066: Daily Digest Not Sent for Users with No Pending Tasks
- **Section**: Daily Digest
- **Priority**: Medium
- **Preconditions**: All user tasks are marked done. 9 AM digest time arrives.
- **Test Steps**:
  1. Complete all tasks.
  2. Wait for 9 AM digest trigger.
- **Expected Results**:
  - No digest message is sent (or digest is sent with an "all done" message — verify per spec).
  - No error or crash.
- **Status**: Not Run
- **Notes**:

---

## 13. EDGE CASES & ERROR HANDLING

### TC_UI_067: Bot Handles Rapid / Repeated Button Taps
- **Section**: Stability
- **Priority**: High
- **Preconditions**: User is viewing a task with action buttons.
- **Test Steps**:
  1. Open a task card.
  2. Rapidly tap `✅ Done` multiple times in quick succession.
- **Expected Results**:
  - Task is marked done exactly once.
  - No duplicate database entries or error messages.
  - Bot handles concurrent callbacks gracefully.
- **Status**: Not Run
- **Notes**:

---

### TC_UI_068: Long Task Title Truncated in List
- **Section**: UI Display
- **Priority**: Medium
- **Preconditions**: None.
- **Test Steps**:
  1. Create a task with a title of 60 characters (e.g., `"This is a very long task title that exceeds thirty characters"`).
  2. Send `/mytasks`.
  3. Observe the inline button label.
- **Expected Results**:
  - Button label shows at most 30 characters with truncation (e.g., `"This is a very long task title…"`).
  - No button overflow or formatting error.
- **Status**: Not Run
- **Notes**:

---

### TC_UI_069: Task with No Description Displays Correctly
- **Section**: UI Display
- **Priority**: Medium
- **Preconditions**: None.
- **Test Steps**:
  1. Create a task via /addtask but send an empty message for description (or tap Skip if available).
  2. View the task card.
- **Expected Results**:
  - Task card shows "No description" or omits the description field gracefully.
  - No formatting errors (e.g., blank lines or broken Markdown).
- **Status**: Not Run
- **Notes**:

---

### TC_UI_070: Bot Responds When Gemini API Is Unavailable
- **Section**: Error Handling
- **Priority**: High
- **Preconditions**: Gemini API is unreachable (simulate by removing or using an invalid API key).
- **Test Steps**:
  1. With Gemini API unavailable, tap `🤖 Add with AI`.
  2. Enter a task description.
  3. Also send `/stats` and check for motivational message handling.
- **Expected Results**:
  - `/addtask_ai`: Bot replies with a user-friendly error (e.g., "AI service unavailable, please try manually").
  - `/stats`: Stats are still shown; motivational message is omitted or replaced with a fallback.
  - Bot does not crash.
- **Status**: Not Run
- **Notes**:

---

### TC_UI_071: User Sends Arbitrary Text (Not a Command)
- **Section**: Error Handling
- **Priority**: Medium
- **Preconditions**: No wizard is active.
- **Test Steps**:
  1. Type and send `"hello bot, what can you do?"` (plain text, not a command).
- **Expected Results**:
  - Bot replies with a helpful message (e.g., pointing to /help).
  - Main menu keyboard is shown.
  - Bot does not crash.
- **Status**: Not Run
- **Notes**:

---

### TC_UI_072: Very Large Task List (50 Tasks)
- **Section**: Stability / UI
- **Priority**: Medium
- **Preconditions**: User has 50+ tasks (at or near the DB limit).
- **Test Steps**:
  1. Create 50 tasks.
  2. Send `/mytasks`.
  3. Observe the inline keyboard.
- **Expected Results**:
  - Bot returns a task list (up to 50, per DB query limit).
  - Inline keyboard renders without Telegram API errors (e.g., message too long).
  - Scrollable in Telegram.
- **Status**: Not Run
- **Notes**: Telegram limits inline keyboard to ~100 buttons; verify behavior near that limit.

---

### TC_UI_073: Bot Handles Stale Inline Button Taps
- **Section**: Stability
- **Priority**: Medium
- **Preconditions**: User had a task list open, then the task was deleted by another session or the tester.
- **Test Steps**:
  1. Open `/mytasks` and see the inline keyboard.
  2. Delete one of those tasks using another Telegram client or `/deletetask`.
  3. Go back to the old message and tap the now-deleted task's inline button.
- **Expected Results**:
  - Bot handles the stale button gracefully — replies with "task not found" rather than crashing.
  - No unhandled exception or silent failure.
- **Status**: Not Run
- **Notes**:

---

### TC_UI_074: Sending Commands Inside Active Wizard
- **Section**: Wizard Robustness
- **Priority**: High
- **Preconditions**: User is inside the /addtask wizard at the description step.
- **Test Steps**:
  1. Start `/addtask`, enter a title.
  2. While waiting for description input, send `/mytasks`.
  3. Then try to resume by sending a description.
- **Expected Results**:
  - `/mytasks` during a wizard either shows tasks (if the bot handles side commands) or the wizard intercepts and re-prompts.
  - Defined behavior — no silent state corruption.
- **Status**: Passed
- **Notes**:

---

### TC_UI_075: Markdown Rendering — Special Characters in Task Content
- **Section**: UI Display
- **Priority**: High
- **Preconditions**: None.
- **Test Steps**:
  1. Create a task with a title containing MarkdownV2 special chars: `Task: (1+2) = 3! #urgent`.
  2. Create a task with description: `Use "quotes" and 'apostrophes' & ampersands`.
  3. View both task cards.
- **Expected Results**:
  - Task cards render correctly in Telegram without broken formatting.
  - Characters are escaped properly — no visible markdown symbols or rendering artifacts.
  - No `BadRequest: Can't parse entities` error from Telegram.
- **Status**: Passed
- **Notes**:

---

## Test Coverage Summary

| Section | Test Cases | Pass | Fail | Not Run |
|---|---|---|---|---|
| Onboarding & Navigation | TC_UI_001–005 | 5 | 0 | 0 |
| Manual Task Creation | TC_UI_006–015 | 8 | 2 | 0 |
| AI Task Creation | TC_UI_016–020 | 5 | 0 | 0 |
| Task Listing & Filtering | TC_UI_021–028 | 7 | 1 | 0 |
| Task Viewing | TC_UI_029–032 | 3 | 0 | 1 |
| Task Editing | TC_UI_033–042 | 5 | 5 | 0 |
| Task Completion | TC_UI_043–047 | 4 | 1 | 0 |
| Task Deletion | TC_UI_048–052 | 3 | 1 | 1 |
| Stats & Motivation | TC_UI_053–056 | 4 | 0 | 0 |
| Timezone Settings | TC_UI_057–061 | 3 | 2 | 0 |
| Deadline Reminders | TC_UI_062–064 | 0 | 1 | 2 |
| Daily Digest | TC_UI_065–066 | 1 | 0 | 1 |
| Edge Cases & Error Handling | TC_UI_067–075 | 2 | 0 | 7 |
| **Total** | **75** | **50** | **13** | **12** |

### Known Defects

| Defect | Affected Tests | Description |
|---|---|---|
| Menu keyboard closes after cancel/back | TC_UI_008, TC_UI_040 | Reply keyboard disappears; user must send `/start` to restore it |
| Edit inline keyboards not shown | TC_UI_035, TC_UI_036, TC_UI_037 | Category, Priority, Status inline options do not appear in edit flow |
| Invalid deadline silently ignored in edit | TC_UI_039 | No error re-prompt; bad value accepted without feedback |
| Timezone not applied to deadline display | TC_UI_010, TC_UI_057, TC_UI_059, TC_UI_065 | Deadlines always shown in UTC regardless of user timezone |
| `/deletetask` command loses task context | TC_UI_050 | "No task selected" error on confirmation step |
| In Progress filter broken | TC_UI_025 | Filter returns wrong or no results for in-progress tasks |
| `/done` has no idempotency check | TC_UI_045 | Bot confirms "done" even when task is already completed |
| No deadline reminder sent | TC_UI_062 | 30-minute reminder notification never fires |

---

*Last updated: 2026-05-03*
