"""
Keyboards — all Telegram InlineKeyboardMarkup layouts.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Upload Notes", callback_data="cmd_upload")],
        [InlineKeyboardButton("📚 View Subjects", callback_data="cmd_subjects")],
        [InlineKeyboardButton("❓ Help", callback_data="cmd_help")],
    ])


def file_action_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Choose Subject", callback_data="action_choose_subject"),
         InlineKeyboardButton("➕ New Subject", callback_data="action_new_subject")],
        [InlineKeyboardButton("📝 Enter Title", callback_data="action_enter_title")],
        [InlineKeyboardButton("📤 Save Note", callback_data="action_upload")],
        [InlineKeyboardButton("❌ Cancel", callback_data="action_cancel")],
    ])


def subject_list_keyboard(subjects: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for sub in subjects:
        rows.append([InlineKeyboardButton(
            f"📁 {sub['name']}", callback_data=f"subject_select:{sub['name']}"
        )])
    rows.append([
        InlineKeyboardButton("⬅️ Back", callback_data="action_back"),
        InlineKeyboardButton("❌ Cancel", callback_data="action_cancel"),
    ])
    return InlineKeyboardMarkup(rows)


def confirm_title_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Use Title", callback_data="title_confirm"),
         InlineKeyboardButton("✏️ Change Title", callback_data="title_change")],
        [InlineKeyboardButton("❌ Cancel", callback_data="action_cancel")],
    ])


def after_upload_keyboard(message_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📨 View in Channel", url=message_link)],
        [InlineKeyboardButton("⬆️ Upload Another File", callback_data="cmd_upload")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="cmd_start")],
    ])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="action_cancel")]
    ])