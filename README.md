# TaskBot AI — Telegram Task Manager

A smart Telegram bot for personal task management, powered by **Google Gemini AI**.
Create tasks in plain English, get auto-categorization, priority prediction, deadline reminders, and a daily productivity digest — all without leaving Telegram.

---

## Features

| Feature | Description |
|---|---|
| **AI Task Creation** | Describe tasks in plain English — Gemini extracts title, deadline, category & priority automatically |
| **Auto-Categorization** | Classifies every task into: work / study / personal / health / finance / general |
| **Priority Prediction** | AI suggests high / medium / low based on urgency language and deadline proximity |
| **Smart Reminders** | Sends a notification 30 minutes before every task deadline |
| **Daily Digest** | Morning summary at 9 AM — top pending tasks + AI-generated motivational message |
| **Productivity Stats** | Completion rate, overdue count, top category, and personalized coaching |
| **Full Task CRUD** | Create, list, filter, view, edit, complete, and delete tasks |
| **Inline Task Actions** | Tap a task in the list to view full details with Done / Edit / Delete inline buttons |
| **Timezone-Aware Deadlines** | Deadlines are stored in UTC and displayed in each user's configured timezone |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Bot Framework | python-telegram-bot 22.6 (async) |
| AI / NLP | Google Gemini API via `google-genai` |
| Database | SQLite via `aiosqlite` (async, local file) |
| Scheduler | APScheduler 3.x (AsyncIOScheduler) |
| Timezones | pytz |
| Config | python-dotenv |
| Testing | pytest + pytest-asyncio + pytest-cov |

---

## Project Structure

```
taskbot/
├── run.py                   # Entry point — start the bot from here
├── requirements.txt
├── .env.example             # Copy to .env and fill in your keys
├── .gitignore
│
├── config/
│   ├── __init__.py
│   └── settings.py          # Centralized env var loading
│
├── app/
│   ├── __init__.py
│   ├── main.py              # Registers all handlers, starts scheduler
│   │
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── handlers.py      # Command handlers (/start, /mytasks, /done, /stats, …)
│   │   ├── conversations.py # ConversationHandlers for /addtask and /edittask flows
│   │   ├── keyboards.py     # ReplyKeyboard and InlineKeyboard builders
│   │   ├── constants.py     # Shared string constants and callback-data prefixes
│   │   └── reminders.py     # Deadline alerts & daily digest scheduler jobs
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py      # Async SQLite CRUD layer
│   │   ├── formatters.py    # MarkdownV2 message formatting helpers
│   │   └── logger.py        # Logging configuration
│   │
│   └── services/
│       ├── __init__.py
│       └── ai_service.py    # Google Gemini integration
│
├── tests/                   # 353 unit tests (pytest-asyncio), 81% coverage
│
└── data/
    └── taskbot.db           # Auto-created on first run (gitignored)
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Get from [@BotFather](https://t.me/BotFather) on Telegram |
| `GEMINI_API_KEY` | Yes | — | Get free from [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| `GEMINI_MODEL` | No | `gemini-1.5-flash` | Use `gemini-1.5-pro` for higher quality |
| `DATABASE_PATH` | No | `data/taskbot.db` | Path to SQLite file |
| `DEFAULT_TIMEZONE` | No | `Asia/Tashkent` | Fallback timezone for reminders |
| `DAILY_SUMMARY_HOUR` | No | `9` | Hour to send morning digest (24h format) |

**Example `.env`:**
```
TELEGRAM_BOT_TOKEN=<your-telegram-token>
GEMINI_API_KEY=<your-gemini-key>
GEMINI_MODEL=gemini-1.5-flash
DEFAULT_TIMEZONE=Asia/Tashkent
DAILY_SUMMARY_HOUR=9
```

---

## Installation & Running Locally

### Step 1 — Get the code

```bash
git clone <your-repo-url>
cd taskbot
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Get your API keys

**Telegram Bot Token:**
1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the token you receive

**Google Gemini API Key:**
1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **Create API Key** and copy it

### Step 4 — Configure environment

```bash
cp .env.example .env
```

Open `.env` and paste your tokens.

### Step 5 — Run

```bash
python run.py
```

You should see:
```
INFO | Database initialised and bot commands registered.
INFO | Reminder scheduler started.
INFO | Bot is running. Press Ctrl+C to stop.
```

Open Telegram, find your bot, and send `/start`.

---

## Bot Commands

### Task Creation
| Command | Description |
|---|---|
| `/addtask` | Step-by-step wizard — title → description → category → priority → deadline |
| `/addtask_ai` | Natural language input — AI parses everything automatically |

### Task Management
| Command | Description |
|---|---|
| `/mytasks` | List all your active tasks (tap any task ID to view full details) |
| `/mytasks pending` | Filter by status: `pending`, `done`, `in_progress` |
| `/mytasks work` | Filter by category: `work`, `study`, `personal`, `health`, `finance`, `general` |
| `/mytask <id>` | View full details for a single task — e.g. `/mytask 3` |
| `/done <id>` | Mark a task as completed — e.g. `/done 3` |
| `/edittask <id>` | Edit any field of a task — e.g. `/edittask 5` |
| `/deletetask <id>` | Delete a task with confirmation prompt — e.g. `/deletetask 2` |

### Insights & Settings
| Command | Description |
|---|---|
| `/stats` | Productivity dashboard — completion rate, overdue count, AI coaching message |
| `/settimezone <tz>` | Set your timezone — e.g. `/settimezone Asia/Tashkent` |
| `/start` | Register your account and see the welcome message |
| `/help` | Show the full command reference inside the bot |

---

## Task Detail View

When you tap a task ID in `/mytasks`, or use `/mytask <id>`, the bot shows a full task card with three inline action buttons:

- **Done** — marks the task complete immediately
- **Edit** — opens the edit flow for any field (title, description, category, priority, deadline, status)
- **Delete** — prompts for confirmation before deleting

---

## AI Examples

Send any of these to `/addtask_ai`:

```
Submit the quarterly report by this Friday, it's urgent
→ Title:    Submit quarterly report
→ Category: work
→ Priority: high
→ Deadline: Friday 09:00
```

```
Buy groceries tomorrow at 5 PM
→ Title:    Buy groceries
→ Category: personal
→ Priority: medium
→ Deadline: tomorrow 17:00
```

```
Study for the math exam next Monday morning
→ Title:    Study for math exam
→ Category: study
→ Priority: high
→ Deadline: next Monday 09:00
```

```
Pay electricity bill sometime this week
→ Title:    Pay electricity bill
→ Category: finance
→ Priority: medium
→ Deadline: null
```

---

## Database Schema

The SQLite database is created automatically at `data/taskbot.db` on first run.

**`users` table**
```
user_id | username | full_name | timezone | language | created_at | last_active
```

**`tasks` table**
```
id | user_id | title | description | status | category | priority | deadline | created_at | updated_at | reminded_at
```

- `status`: `pending` | `in_progress` | `done` | `cancelled`
- `category`: `work` | `study` | `personal` | `health` | `finance` | `general`
- `priority`: `high` | `medium` | `low`
- `deadline`: stored as UTC ISO-8601 (`YYYY-MM-DDTHH:MM:SS`), displayed in the user's configured timezone

---

## Running Tests

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

Current status: **353 / 353 passing**, ~81% coverage.

---

## Notes

- All data is stored **locally** in SQLite — no external database or cloud storage required
- Each user's tasks are fully isolated by their Telegram `user_id`
- Deadline reminders fire **30 minutes before** the deadline, at most once per hour per task
- The daily digest respects each user's individual timezone setting
- The bot uses Telegram's **MarkdownV2** formatting throughout

