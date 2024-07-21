from pyrogram import Client, filters
from telegram.ext import ApplicationBuilder
from pyrogram.handlers import CallbackQueryHandler
from .config import api_id, api_hash, bot_token, OWNER_ID as BOT_OWNER
from .handlers.start import start
from .handlers.upload import upload , edit_character
from .handlers.inliner import inline_query_handler
from .handlers.search import search, send_inline_query_button
from .handlers.drop import droptime, check_message_count
from .handlers.smash import smash_image
from .handlers.collection import smashes  # Import the new handler
from .handlers.gift import gift_character , confirm_gift , cancel_gift

# Pyrogram Client instance
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Register the start handler for Pyrogram
app.on_message(filters.command("start") & filters.private)(start)
app.on_message(filters.command("upload") & filters.user(BOT_OWNER))(upload)
app.on_message(filters.command("edit") & filters.user(BOT_OWNER))(edit_character)
app.on_message(filters.command("search"))(search)
app.on_message(filters.command("droptime") & filters.group)(droptime)
app.on_message(filters.command("smash") & filters.group)(smash_image)
app.on_message(filters.command("smashes"))(smashes)  # Register the new command handler
app.on_message(filters.command("s") & filters.private)(send_inline_query_button)  # Register the new command handler
app.on_message(filters.command("gift") & filters.group & filters.reply)(gift_character)  # Register the gift command handler

# Register callback query handlers
app.add_handler(CallbackQueryHandler(confirm_gift, filters.regex(r"^confirm_gift\|")))
app.add_handler(CallbackQueryHandler(cancel_gift, filters.regex(r"^cancel_gift\|")))


# Filter to exclude commands
non_command_filter = filters.group & ~filters.regex(r"^/")

# Register message handler with non-command filter
app.on_message((filters.text | filters.media) & non_command_filter)(check_message_count)

# PYTHON-TELEGRAM-BOT Instance
pbot = ApplicationBuilder().token(bot_token).build()

# Register the inline query handler for pbot
pbot.add_handler(inline_query_handler)

def run_pyro_bot():
    app.run()

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
