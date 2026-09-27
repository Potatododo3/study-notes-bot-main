"""Telegram storage for notes organized into forum topics by subject."""

import json
import logging
import os
import asyncio

logger = logging.getLogger(__name__)
INDEX_PREFIX = "STUDY_NOTES_INDEX:"


class TelegramStorage:
    def __init__(self):
        channel = os.environ.get("TELEGRAM_STORAGE_CHANNEL")
        if not channel:
            raise EnvironmentError("TELEGRAM_STORAGE_CHANNEL env var not set.")
        self.channel = channel
        self._index_path = os.environ.get("TOPIC_INDEX_PATH", "data/topics.json")
        self._topic_lock = asyncio.Lock()

    def _read_local_index(self) -> dict:
        try:
            with open(self._index_path, "r", encoding="utf-8") as index_file:
                value = json.load(index_file)
            return {"subjects": list(value.get("subjects", [])), "topics": dict(value.get("topics", {}))}
        except FileNotFoundError:
            return {"subjects": [], "topics": {}}
        except (OSError, ValueError, TypeError):
            logger.exception("Could not read local topic index %s", self._index_path)
            return {"subjects": [], "topics": {}}

    def _write_local_index(self, index: dict):
        directory = os.path.dirname(os.path.abspath(self._index_path))
        os.makedirs(directory, exist_ok=True)
        temporary_path = self._index_path + ".tmp"
        with open(temporary_path, "w", encoding="utf-8") as index_file:
            json.dump(index, index_file, ensure_ascii=False)
            index_file.flush()
            os.fsync(index_file.fileno())
        os.replace(temporary_path, self._index_path)

    def _make_caption(self, subject: str, title: str) -> str:
        return f"📁 {subject} | 📝 {title}"

    async def _read_index(self, bot) -> dict:
        chat = await bot.get_chat(self.channel)
        pinned = chat.pinned_message
        local = self._read_local_index()
        if not pinned or not pinned.text:
            return local

        text = pinned.text
        if text.startswith(INDEX_PREFIX):
            try:
                index = json.loads(text[len(INDEX_PREFIX):])
                index = {
                    "subjects": list(index.get("subjects", [])),
                    "topics": dict(index.get("topics", {})),
                }
            except (ValueError, TypeError):
                logger.warning("The pinned study notes index could not be parsed.")
                return local
        # Preserve indexes created by earlier versions of the bot.
        if text.startswith("SUBJECTS:"):
            subjects = [s.strip() for s in text[len("SUBJECTS:"):].split(",") if s.strip()]
            index = {"subjects": subjects, "topics": {}}
        elif not text.startswith(INDEX_PREFIX):
            return local

        for subject in local["subjects"]:
            if subject not in index["subjects"]:
                index["subjects"].append(subject)
        index["topics"].update(local["topics"])
        return index

    async def _write_index(self, bot, index: dict):
        text = INDEX_PREFIX + json.dumps(index, ensure_ascii=False, separators=(",", ":"))
        if len(text) > 4096:
            raise RuntimeError("The subject index is too large for Telegram's pinned-message limit.")
        # Keep a local recovery copy as well as the pinned group index.
        self._write_local_index(index)
        chat = await bot.get_chat(self.channel)
        pinned = chat.pinned_message
        if pinned and pinned.text and (pinned.text.startswith(INDEX_PREFIX) or pinned.text.startswith("SUBJECTS:")):
            await bot.edit_message_text(chat_id=self.channel, message_id=pinned.message_id, text=text)
        else:
            msg = await bot.send_message(chat_id=self.channel, text=text)
            await bot.pin_chat_message(
                chat_id=self.channel,
                message_id=msg.message_id,
                disable_notification=True,
            )

    async def _get_or_create_topic(self, bot, subject: str) -> int:
        async with self._topic_lock:
            index = await self._read_index(bot)
            thread_id = index["topics"].get(subject)
            if thread_id is not None:
                return int(thread_id)

            # Check the group before creating anything and ensure the new index fits.
            chat = await bot.get_chat(self.channel)
            if not getattr(chat, "is_forum", False):
                raise RuntimeError("Storage chat is not a topics-enabled forum group.")
            candidate = {"subjects": list(index["subjects"]), "topics": dict(index["topics"])}
            if subject not in candidate["subjects"]:
                candidate["subjects"].append(subject)
            candidate["topics"][subject] = 9999999999
            candidate_text = INDEX_PREFIX + json.dumps(candidate, ensure_ascii=False, separators=(",", ":"))
            if len(candidate_text) > 4096:
                raise RuntimeError("The subject index is full. Remove old subjects before adding another.")

            topic = await bot.create_forum_topic(chat_id=self.channel, name=subject[:128])
            index["topics"][subject] = topic.message_thread_id
            if subject not in index["subjects"]:
                index["subjects"].append(subject)
            # Local persistence lets a retry recover if editing/pinning the group index fails.
            try:
                self._write_local_index(index)
                await self._write_index(bot, index)
            except Exception as error:
                logger.exception("Created forum topic %s but could not save its index", topic.message_thread_id)
                raise RuntimeError(
                    f"Created topic '{subject}' (topic ID {topic.message_thread_id}), but could not save its index: {error}"
                ) from error
            return topic.message_thread_id

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
