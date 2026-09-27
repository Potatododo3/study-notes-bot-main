# 📚 Study Notes Organizer Bot — Setup Guide

---

## Overview

This bot lets you send PDF/JPG/PNG files to Telegram and organizes them into a private forum group, with one topic per subject and subject/title captions.

---

## Project Structure

```
study-notes-bot/
├── main.py
├── requirements.txt
├── bot/
│   ├── handlers.py
│   └── keyboards.py
├── storage/
│   ├── __init__.py
│   └── telegram_storage.py
└── session/
    ├── __init__.py
    └── session_manager.py
```

---

## Step 1 — Create Your Bot

1. Open Telegram and message **@BotFather**
2. Send `/newbot`
3. Follow the steps and copy your **bot token**

---

## Step 2 — Create a Private Forum Storage Group

1. Create a new **Private** Telegram group and enable **Topics** in the group settings.
2. Add your bot as an **Admin** with permissions to post messages, manage topics, and pin messages.
3. Get the group ID by forwarding any message from the group to **@userinfobot**
   - It will look like `-1001234567890`

---

## Step 3 — Configure Environment Variables

Set these in Portainer or your `.env` file:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_STORAGE_CHANNEL=-1001234567890
```

---

## Step 4 — Transfer Files to Server

Use **WinSCP** to copy the project folder to your Ubuntu server, then start the container via Portainer.

Startup command:
```
sh -c "pip install -q -r /app/requirements.txt && python /app/main.py"
```

---

## Using the Bot

| Command | Action |
|---|---|
| `/start` | Show main menu |
| `/subjects` | List all subjects |
| `/help` | Show usage instructions |

**Upload flow:**
1. Send any PDF, JPG, or PNG to the bot
2. Tap **📚 Choose Subject** or **➕ New Subject**
3. Tap **📝 Enter Title** and type your note title
4. Tap **📤 Save Note**
5. Done! The bot creates a forum topic for the subject when needed, then saves the file there with caption `📁 Subject | 📝 Title`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `TELEGRAM_BOT_TOKEN not set` | Check your env vars in Portainer |
| `TELEGRAM_STORAGE_CHANNEL not set` | Add the channel ID env var |
| Bot can't post or create topics | Make sure storage is a topics-enabled group and the bot can post, manage topics, and pin messages |
| File too large | Telegram has a 20MB bot file size limit |
