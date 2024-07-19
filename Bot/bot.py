# Bot/bot.py

from pyrogram import Client, filters
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from .config import api_id, api_hash, bot_token , OWNER_ID as BOT_OWNER
from .handlers.start import start
from .handlers.upload import upload
from .handlers.inliner import inline_query_handler
from .handlers.search import search
from .handlers.drop import droptime, check_message_count, handle_new_chat


# Pyrogram Client instance
bot = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Register the start handler for Pyrogram
bot.on_message(filters.command("start") & filters.private)(start)
bot.on_message(filters.command("upload") & filters.user(BOT_OWNER))(upload)
bot.on_message(filters.command("search") & filters.private)(search)  # Add this line
bot.on_message(filters.command("droptime") & filters.group)(droptime)

# Register message handler to count messages
non_command_filter = filters.group & ~filters.regex(r"^/")
bot.on_message((filters.text | filters.media) & non_command_filter)(check_message_count)

# Handle bot being added to a new chat
bot.on_chat_member_updated()(handle_new_chat)



#PYTHON-TELEGRAM-BOT Instance
pbot = ApplicationBuilder().token(bot_token).build()

# Register the inline query handler for pbot
pbot.add_handler(inline_query_handler)

def run_pyro_bot():
    bot.run()

def run_telegram_bot():
    pbot.run_polling()

def main():
    from multiprocessing import Process

    p1 = Process(target=run_pyro_bot)
    p2 = Process(target=run_telegram_bot)
    p1.start()
    p2.start()
    p1.join()
    p2.join()
