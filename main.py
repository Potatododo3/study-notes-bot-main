"""
main.py — Study Notes Organizer Bot entry point.
"""

import logging
import os
from dotenv import load_dotenv

# Load local development settings before importing modules that read them.
load_dotenv()

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from bot.handlers import (
    cmd_start,
    cmd_subjects,
    cmd_help,
    handle_file,
    handle_text,
    handle_callback,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN env var is not set.")

    app = ApplicationBuilder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("subjects", cmd_subjects))
    app.add_handler(CommandHandler("help", cmd_help))

    # Files
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))

    # Text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Button callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("🤖 Study Notes Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
