"""
app/bot/constants.py — Centralized constants for handlers.

Consolidates all magic strings, patterns, and configuration values
to follow DRY principles and improve maintainability.
"""

from enum import IntEnum, Enum
from typing import Dict, Tuple, List

# =============================================================================
#  CONVERSATION STATES (IntEnum for better type safety)
# =============================================================================

class ConversationState(IntEnum):
    """Conversation state constants for AddTask and EditTask flows."""
    # /addtask — Manual wizard
    AT_TITLE = 0
    AT_DESCRIPTION = 1
    AT_CATEGORY = 2
    AT_PRIORITY = 3
    AT_DEADLINE = 4
    
    # /addtask_ai — Natural language
    AI_INPUT = 5
    
    # /edittask — Edit flow
    EDIT_ID = 6
    EDIT_FIELD = 7
    EDIT_VALUE = 8


# =============================================================================
#  CALLBACK DATA PATTERNS (Constants for all button callbacks)
# =============================================================================

class CallbackPattern(str, Enum):
    """Callback data pattern prefixes — enables consistent pattern matching."""
    # Menu actions
    MENU_MAIN = "menu_main"
    MENU_FILTERS = "menu_filters"
    MENU_TIMEZONE = "menu_timezone"
    MENU_ADDTASK = "menu_addtask"
    MENU_ADDTASK_AI = "menu_addtask_ai"
    MENU_MYTASKS = "menu_mytasks"
    MENU_STATS = "menu_stats"
    
    # Filter actions
    FILTER = "filter_"  # filter_pending, filter_done, etc.
    
    # Timezone actions
    TIMEZONE = "tz_"    # tz_Asia/Tashkent, etc.
    
    # Task actions
    TASK_VIEW = "task_view_"
    TASK_DONE = "task_done_"
    TASK_EDIT = "task_edit_"
    TASK_DELETE = "task_del_"
    TASK_DELETE_CONFIRM = "task_del_confirm_"
    
    # Wizard inline buttons
    WIZARD_SKIP = "wz_skip"
    WIZARD_CATEGORY = "wz_cat_"
    WIZARD_PRIORITY = "wz_pri_"


# =============================================================================
#  FILTER & STATUS MAPPINGS (Single source of truth)
# =============================================================================

FILTER_MAP: Dict[str, Tuple[str, None]] = {
    "filter_pending":  ("pending", None),
    "filter_done":     ("done", None),
    "filter_progress": ("in_progress", None),
}

CATEGORY_MAP: Dict[str, Tuple[None, str]] = {
    "filter_work":     (None, "work"),
    "filter_study":    (None, "study"),
    "filter_personal": (None, "personal"),
    "filter_health":   (None, "health"),
    "filter_finance":  (None, "finance"),
}

# Combined filter map for easy lookup
ALL_FILTERS: Dict[str, Tuple] = {**FILTER_MAP, **CATEGORY_MAP}


# =============================================================================
#  TIMEZONE DEFINITIONS (Curated list with emoji + label)
# =============================================================================

COMMON_TIMEZONES: List[Tuple[str, str]] = [
    ("🌍 Tashkent", "Asia/Tashkent"),
    ("🌍 Almaty", "Asia/Almaty"),
    ("🌍 Dubai", "Asia/Dubai"),
    ("🌍 Moscow", "Europe/Moscow"),
    ("🌍 London", "Europe/London"),
    ("🌍 Berlin", "Europe/Berlin"),
    ("🌍 New York", "America/New_York"),
    ("🌍 Los Angeles", "America/Los_Angeles"),
    ("🌍 Tokyo", "Asia/Tokyo"),
    ("🌍 Sydney", "Australia/Sydney"),
    ("🌍 UTC", "UTC"),
]

# Create reverse mapping: tz_name -> label (for callback handling)
TIMEZONE_BY_NAME: Dict[str, str] = {tz[1].replace("/", "_"): tz[1] for tz in COMMON_TIMEZONES}


# =============================================================================
#  DEADLINE FORMATS (DRY list of supported formats)
# =============================================================================

DATE_FORMATS: List[str] = [
    "%Y-%m-%d %H:%M",      # 2026-03-15 14:30
    "%Y-%m-%d %H:%M:%S",   # 2026-03-15 14:30:00
    "%Y-%m-%dT%H:%M:%S",   # 2026-03-15T14:30:00
    "%Y-%m-%dT%H:%M",      # 2026-03-15T14:30
    "%Y-%m-%d",            # 2026-03-15
    "%d/%m/%Y %H:%M",      # 15/03/2026 14:30
    "%d/%m/%Y",            # 15/03/2026
    "%d.%m.%Y %H:%M",      # 15.03.2026 14:30
    "%d.%m.%Y",            # 15.03.2026
    "%d-%m-%Y %H:%M",      # 15-03-2026 14:30
    "%d-%m-%Y",            # 15-03-2026
    "%m/%d/%Y %H:%M",      # 03/15/2026 14:30
    "%m/%d/%Y",            # 03/15/2026
]

WEEKDAYS: List[str] = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday"
]


# =============================================================================
#  EDIT FIELDS (Task edit wizard options)
# =============================================================================

EDIT_FIELDS: List[str] = [
    "Title", "Description", "Category", "Priority", "Deadline", "Status"
]

EDIT_STATUS_OPTIONS: List[str] = [
    "pending", "in_progress", "done", "cancelled"
]


# =============================================================================
#  ERROR MESSAGES (User-facing messages)
# =============================================================================

ERROR_MESSAGES: Dict[str, str] = {
    "invalid_timezone": "⚠️ Invalid timezone `{}`\\. Please try again\\.",
    "invalid_deadline": (
        "I couldn't understand that date\\. Try one of these formats:\n"
        "`2026-03-15 14:30` or `15/03/2026 14:30`\n"
        "or type: `tomorrow`, `today`, `next monday`, `in 3 days`"
    ),
    "invalid_field": "⚠️ Unknown field\\. Choose from the keyboard\\.",
    "task_not_found": "⚠️ Task `#{task_id}` not found\\.",
    "already_done": "Already marked as done\\.",
    "generic_error": (
        "⚠️ Something went wrong while processing your request\\.\n"
        "Please try again or use /help\\."
    ),
}


# =============================================================================
#  TEXT TEMPLATES (User messages)
# =============================================================================

WIZARD_STEPS: Dict[int, str] = {
    1: "📝 *New Task — Step 1/5*\n\nWhat is the task *title*?",
    2: "💬 *Step 2/5*\n\nAdd a description \\(or skip\\):",
    3: "🏷️ *Step 3/5*\n\nChoose a category:",
    4: "⚡ *Step 4/5*\n\nSet priority:",
    5: "🕐 *Step 5/5*\n\nSet a deadline \\(or skip\\):",
}


# =============================================================================
#  UTILITY FUNCTIONS FOR CALLBACK DATA PARSING
# =============================================================================

def extract_id_from_callback(callback_data: str, pattern_prefix: str) -> int:
    """Extract numeric ID from callback data.
    
    Args:
        callback_data: The full callback_data string (e.g., "task_view_42")
        pattern_prefix: The pattern prefix (e.g., "task_view_")
    
    Returns:
        The extracted ID as integer
    
    Raises:
        ValueError: If ID cannot be extracted or is invalid
    """
    if not callback_data.startswith(pattern_prefix):
        raise ValueError(f"Callback data doesn't match pattern {pattern_prefix}")
    
    try:
        id_str = callback_data[len(pattern_prefix):]
        return int(id_str)
    except (ValueError, IndexError) as e:
        raise ValueError(f"Could not extract ID from callback_data '{callback_data}': {e}")
