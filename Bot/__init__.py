from pyrogram import Client, filters
from pyrogram.types import Message
from telegram.ext import ApplicationBuilder
from .config import api_id, api_hash, bot_token, OWNER_ID as BOT_OWNER


# Pyrogram Client instance
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# PYTHON-TELEGRAM-BOT Instance
pbot = ApplicationBuilder().token(bot_token).build()