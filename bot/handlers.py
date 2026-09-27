"""
Handlers — Telegram command, message, and callback handlers.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.keyboards import (
    main_menu_keyboard,
    file_action_keyboard,
    subject_list_keyboard,
    confirm_title_keyboard,
    after_upload_keyboard,
    cancel_keyboard,
)
from session.session_manager import session_manager
from storage.telegram_storage import telegram_storage

logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "👋 *Welcome to Study Notes Organizer!*\n\n"
    "I help you save and organize your study files.\n\n"
    "📄 Send me any *PDF, JPG, or PNG* file to get started, or use the menu below."
)

HELP_TEXT = (
    "📖 *How to use this bot:*\n\n"
    "1️⃣ Send a PDF, JPG, or PNG file\n"
    "2️⃣ Choose or create a *Subject*\n"
    "3️⃣ Enter a *Title* for this note\n"
    "4️⃣ Tap *Save Note* ✅\n\n"
    "Your file will be saved with the caption:\n"
    "`📁 Subject | 📝 Title`\n\n"
    "📌 Commands:\n"
    "/start — Main menu\n"
    "/subjects — List all subjects\n"
    "/help — Show this message"
)


# ── Commands ───────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session_manager.reset(chat_id)
    await update.effective_message.reply_text(
        WELCOME_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(),
    )


async def cmd_subjects(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _show_subjects_info(update, ctx)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        HELP_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(),
    )


# ── File received ──────────────────────────────────────────────────────────

async def handle_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat_id = msg.chat_id

    if msg.document:
        mime = msg.document.mime_type or "application/octet-stream"
        if mime not in ("application/pdf", "image/jpeg", "image/png"):
            await msg.reply_text("⚠️ Please send a *PDF, JPG, or PNG* file.", parse_mode=ParseMode.MARKDOWN)
            return
        file_id = msg.document.file_id
        file_name = msg.document.file_name or "file"
    elif msg.photo:
        photo = msg.photo[-1]
        file_id = photo.file_id
        file_name = f"photo_{photo.file_id[-6:]}.jpg"
        mime = "image/jpeg"
    else:
        await msg.reply_text("⚠️ Unsupported file type. Please send PDF, JPG, or PNG.")
        return

    session_manager.update(chat_id, file_id=file_id, file_name=file_name, file_mime=mime, step="file_received")
    session = session_manager.get(chat_id)

    status = _build_status(session)
    await msg.reply_text(
        f"📎 *File received:* `{file_name}`\n\n{status}\n\nWhat would you like to do?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=file_action_keyboard(),
    )


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat_id = msg.chat_id
    session = session_manager.get(chat_id)
    text = msg.text.strip()

    if session.step == "awaiting_subject":
        session_manager.update(chat_id, subject=text, step="file_received")
        session = session_manager.get(chat_id)
        status = _build_status(session)
        await msg.reply_text(
            f"✅ Subject set to *{text}*\n\n{status}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=file_action_keyboard(),
        )

    elif session.step == "awaiting_title":
        session_manager.update(chat_id, title=text, step="confirming_title")
        await msg.reply_text(
            f"📝 Title entered: *{text}*\n\nLooks good?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=confirm_title_keyboard(),
        )

    else:
        await msg.reply_text(
            "📬 Send me a file to get started, or use /start",
            reply_markup=main_menu_keyboard(),
        )


# ── Callbacks ──────────────────────────────────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data
    session = session_manager.get(chat_id)

    if data == "cmd_start":
        session_manager.reset(chat_id)
        await query.edit_message_text(
            WELCOME_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard()
        )
        return

    if data == "cmd_upload":
        session_manager.reset(chat_id)
        await query.edit_message_text(
            "📎 *Send me your file!*\n\nSupported formats: PDF, JPG, PNG",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=cancel_keyboard(),
        )
        return

    if data == "cmd_subjects":
        await _show_subjects_callback(query, ctx)
        return

    if data == "cmd_help":
        await query.edit_message_text(
            HELP_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard()
        )
        return

    if data == "action_choose_subject":
        subjects = await telegram_storage.list_subjects(ctx.bot)
        if not subjects:
            await query.edit_message_text(
                "📭 *No subjects found yet.*\n\nTap *➕ New Subject* to create one.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=file_action_keyboard(),
            )
        else:
            subject_dicts = [{"name": s} for s in subjects]
            await query.edit_message_text(
                "📚 *Choose a subject:*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=subject_list_keyboard(subject_dicts),
            )
        return

    if data == "action_new_subject":
        session_manager.update(chat_id, step="awaiting_subject")
        await query.edit_message_text(
            "✏️ *Enter a new subject name:*\n\n_(Type and send it as a message)_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=cancel_keyboard(),
        )
        return

    if data == "action_enter_title":
        if not session.subject:
            await query.answer("⚠️ Please choose a subject first!", show_alert=True)
            return
        session_manager.update(chat_id, step="awaiting_title")
        await query.edit_message_text(
            "📝 *Enter the note title:*\n\n_(Type and send it as a message)_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=cancel_keyboard(),
        )
        return

    if data == "action_upload":
        await _do_upload(query, chat_id, session, ctx)
        return

    if data == "action_back":
        session_manager.update(chat_id, step="file_received")
        session = session_manager.get(chat_id)
        status = _build_status(session)
        await query.edit_message_text(
            f"📎 *File:* `{session.file_name}`\n\n{status}\n\nWhat would you like to do?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=file_action_keyboard(),
        )
        return

    if data == "action_cancel":
        session_manager.reset(chat_id)
        await query.edit_message_text(
            "❌ *Cancelled.*\n\nSend a new file or use /start",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(),
        )
        return

    if data.startswith("subject_select:"):
        subject = data.split(":", 1)[1]
        session_manager.update(chat_id, subject=subject, step="file_received")
        session = session_manager.get(chat_id)
        status = _build_status(session)
        await query.edit_message_text(
            f"✅ Subject set to *{subject}*\n\n{status}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=file_action_keyboard(),
        )
        return

    if data == "title_confirm":
        session_manager.update(chat_id, step="file_received")
        session = session_manager.get(chat_id)
        status = _build_status(session)
        await query.edit_message_text(
            f"✅ Title confirmed!\n\n{status}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=file_action_keyboard(),
        )
        return

    if data == "title_change":
        session_manager.update(chat_id, title=None, step="awaiting_title")
        await query.edit_message_text(
            "✏️ *Enter a new title:*\n\n_(Type and send it as a message)_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=cancel_keyboard(),
        )
        return


# ── Upload logic ───────────────────────────────────────────────────────────

async def _do_upload(query, chat_id: int, session, ctx: ContextTypes.DEFAULT_TYPE):
    if not session.file_id:
        await query.answer("⚠️ No file found! Send a file first.", show_alert=True)
        return
    if not session.subject:
        await query.answer("⚠️ Please choose a subject first!", show_alert=True)
        return
    if not session.title:
        await query.answer("⚠️ Please enter a title first!", show_alert=True)
        return

    await query.edit_message_text(
        "⏳ *Saving note...*\n\nPlease wait a moment.",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        result = await telegram_storage.upload_file(
            bot=ctx.bot,
            file_id=session.file_id,
            file_name=session.file_name,
            mime_type=session.file_mime,
            subject=session.subject,
            title=session.title,
        )

        await telegram_storage.save_subject(ctx.bot, session.subject)

        success_text = (
            "✅ *Note saved!*\n\n"
            f"📁 Subject: *{session.subject}*\n"
            f"📝 Title: *{session.title}*\n"
            f"📄 File: `{session.file_name}`"
        )
        await query.edit_message_text(
            success_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=after_upload_keyboard(result["message_link"]),
            disable_web_page_preview=True,
        )
        session_manager.reset(chat_id)

    except Exception as e:
        logger.exception("Save failed")
        await query.edit_message_text(
            f"❌ *Save failed.*\n\n`{str(e)}`\n\nPlease try again.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=file_action_keyboard(),
        )


# ── Helpers ────────────────────────────────────────────────────────────────

def _build_status(session) -> str:
    subject_str = f"✅ *{session.subject}*" if session.subject else "❌ Not set"
    title_str = f"✅ *{session.title}*" if session.title else "❌ Not set"
    return f"📁 Subject: {subject_str}\n📝 Title: {title_str}"


async def _show_subjects_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    subjects = await telegram_storage.list_subjects(ctx.bot)
    if not subjects:
        text = "📭 *No subjects yet.*\n\nSend a file and create your first subject!"
    else:
        lines = "\n".join(f"  📁 {s}" for s in subjects)
        text = f"📚 *Your Subjects ({len(subjects)}):*\n\n{lines}"
    await update.effective_message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard()
    )


async def _show_subjects_callback(query, ctx: ContextTypes.DEFAULT_TYPE):
    subjects = await telegram_storage.list_subjects(ctx.bot)
    if not subjects:
        text = "📭 *No subjects yet.*\n\nSend a file and create your first subject!"
    else:
        lines = "\n".join(f"  📁 {s}" for s in subjects)
        text = f"📚 *Your Subjects ({len(subjects)}):*\n\n{lines}"
    await query.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard()
    )