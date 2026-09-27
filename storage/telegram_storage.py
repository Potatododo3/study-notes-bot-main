"""Telegram storage for notes organized into forum topics by subject."""

import json
import logging
import os

logger = logging.getLogger(__name__)
INDEX_PREFIX = "STUDY_NOTES_INDEX:"


class TelegramStorage:
    def __init__(self):
        channel = os.environ.get("TELEGRAM_STORAGE_CHANNEL")
        if not channel:
            raise EnvironmentError("TELEGRAM_STORAGE_CHANNEL env var not set.")
        self.channel = channel

    def _make_caption(self, subject: str, title: str) -> str:
        return f"📁 {subject} | 📝 {title}"

    async def _read_index(self, bot) -> dict:
        chat = await bot.get_chat(self.channel)
        pinned = chat.pinned_message
        if not pinned or not pinned.text:
            return {"subjects": [], "topics": {}}

        text = pinned.text
        if text.startswith(INDEX_PREFIX):
            try:
                index = json.loads(text[len(INDEX_PREFIX):])
                return {
                    "subjects": list(index.get("subjects", [])),
                    "topics": dict(index.get("topics", {})),
                }
            except (ValueError, TypeError):
                logger.warning("The pinned study notes index could not be parsed.")
        # Preserve indexes created by earlier versions of the bot.
        if text.startswith("SUBJECTS:"):
            subjects = [s.strip() for s in text[len("SUBJECTS:"):].split(",") if s.strip()]
            return {"subjects": subjects, "topics": {}}
        return {"subjects": [], "topics": {}}

    async def _write_index(self, bot, index: dict):
        text = INDEX_PREFIX + json.dumps(index, ensure_ascii=False, separators=(",", ":"))
        chat = await bot.get_chat(self.channel)
        pinned = chat.pinned_message
        if pinned:
            await bot.edit_message_text(chat_id=self.channel, message_id=pinned.message_id, text=text)
        else:
            msg = await bot.send_message(chat_id=self.channel, text=text)
            await bot.pin_chat_message(
                chat_id=self.channel,
                message_id=msg.message_id,
                disable_notification=True,
            )

    async def _get_or_create_topic(self, bot, subject: str) -> int:
        index = await self._read_index(bot)
        thread_id = index["topics"].get(subject)
        if thread_id is not None:
            return int(thread_id)

        topic = await bot.create_forum_topic(chat_id=self.channel, name=subject[:128])
        thread_id = topic.message_thread_id
        if subject not in index["subjects"]:
            index["subjects"].append(subject)
        index["topics"][subject] = thread_id
        # Save immediately so a restart will reuse the topic we just created.
        await self._write_index(bot, index)
        return thread_id

    async def upload_file(self, bot, file_id: str, file_name: str, mime_type: str, subject: str, title: str) -> dict:
        thread_id = await self._get_or_create_topic(bot, subject)
        caption = self._make_caption(subject, title)

        if mime_type in ("image/jpeg", "image/png"):
            msg = await bot.send_photo(
                chat_id=self.channel,
                photo=file_id,
                caption=caption,
                message_thread_id=thread_id,
            )
        else:
            msg = await bot.send_document(
                chat_id=self.channel,
                document=file_id,
                caption=caption,
                filename=file_name,
                message_thread_id=thread_id,
            )

        chat_id = str(self.channel)
        internal_chat_id = chat_id[4:] if chat_id.startswith("-100") else chat_id.lstrip("-")
        msg_link = f"https://t.me/c/{internal_chat_id}/{thread_id}/{msg.message_id}"
        return {"message_id": msg.message_id, "message_link": msg_link}

    async def list_subjects(self, bot) -> list[str]:
        try:
            return (await self._read_index(bot))["subjects"]
        except Exception:
            logger.exception("Could not read the pinned subject index")
            return []

    async def save_subject(self, bot, subject: str):
        """Keep the subject index current (topics are created when the first note is saved)."""
        try:
            index = await self._read_index(bot)
            if subject not in index["subjects"]:
                index["subjects"].append(subject)
                await self._write_index(bot, index)
        except Exception:
            logger.exception("Could not save subject")


telegram_storage = TelegramStorage()
