from pyrogram import Client, filters
from pyrogram.types import Message
from telegram.ext import ApplicationBuilder
from pyrogram.handlers import CallbackQueryHandler, ChatMemberUpdatedHandler
from .config import api_id, api_hash, bot_token, OWNER_ID as BOT_OWNER
from .handlers.start import start
from .handlers.upload import upload, edit_character
from .handlers.inliner import inline_query_handler
from .handlers.search import search, send_inline_query_button
from .handlers.drop import droptime, check_message_count, handle_new_member
from .handlers.smash import smash_image
from .handlers.collection import smashes
from .handlers.gift import gift_character, confirm_gift, cancel_gift
from .handlers.trade import initiate_trade, handle_trade_callback
from .handlers.daan import daan
from .handlers.sinfo import sinfo, delete_collection, close_sinfo
from .handlers.privacy import ban, unban, add_sudo, remove_sudo
from .database import is_user_banned, is_user_sudo
from .handlers.preference import set_fav, unfav, smode, smode_default, smode_sort, smode_rarity, smode_close, fav_confirm, fav_cancel
from .handlers.leaderboard import top, stop
from .handlers.mic import check_character

# Pyrogram Client instance
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Custom filter to check if a user is banned
async def command_filter(_, __, message: Message):
    if await is_user_banned(message.from_user.id):
        return False
    return True

# Custom filter to check if a user is sudo or owner
async def sudo_filter(_, __, message: Message):
    if message.from_user.id == BOT_OWNER or await is_user_sudo(message.from_user.id):
        return True
    return False

command_filter = filters.create(command_filter)
sudo_filter = filters.create(sudo_filter)

# Register handlers
app.on_message(filters.command("start") & filters.private & command_filter)(start)
app.on_message(filters.command("upload") & sudo_filter)(upload)
app.on_message(filters.command("edit") & sudo_filter)(edit_character)
app.on_message(filters.command("search") & command_filter)(search)
app.on_message(filters.command("droptime") & filters.group & command_filter)(droptime)
app.on_message(filters.command("smash") & filters.group & command_filter)(smash_image)
app.on_message(filters.command("smashes") & command_filter)(smashes)
app.on_message(filters.command("s") & filters.private & command_filter)(send_inline_query_button)
app.on_message(filters.command("gift") & filters.group & filters.reply & command_filter)(gift_character)
app.on_message(filters.command("daan") & sudo_filter)(daan)
app.on_message(filters.command("sinfo") & sudo_filter)(sinfo)
app.on_message(filters.command("bang") & sudo_filter)(ban)
app.on_message(filters.command("unbang") & sudo_filter)(unban)
app.on_message(filters.command("sudo") & filters.user(BOT_OWNER))(add_sudo)
app.on_message(filters.command("rmsudo") & filters.user(BOT_OWNER))(remove_sudo)
app.on_message(filters.command("fav") & command_filter)(set_fav)
app.on_message(filters.command("unfav") & command_filter)(unfav)
app.on_message(filters.command("smode") & command_filter)(smode)
app.on_message(filters.command("top") & filters.group & command_filter)(top)
app.on_message(filters.command("smtop") & command_filter)(stop)
app.on_message(filters.command("check") & filters.group & command_filter)(check_character)

# Register the command and callback handlers
app.on_message(filters.command("trade") & filters.reply & filters.group & command_filter)(initiate_trade)
app.on_callback_query(filters.regex(r"^(confirm_trade|cancel_trade)\|") & command_filter)(handle_trade_callback)
app.add_handler(CallbackQueryHandler(confirm_gift, filters.regex(r"^confirm_gift\|") & command_filter))
app.add_handler(CallbackQueryHandler(cancel_gift, filters.regex(r"^cancel_gift\|") & command_filter))
app.add_handler(CallbackQueryHandler(delete_collection, filters.regex(r"^delete_collection_") & command_filter))
app.add_handler(CallbackQueryHandler(close_sinfo, filters.regex(r"^close_sinfo") & command_filter))
app.on_callback_query(filters.regex(r"^fav_confirm:\d+:\d+$"))(fav_confirm)
app.on_callback_query(filters.regex(r"^fav_cancel:\d+$"))(fav_cancel)
app.on_callback_query(filters.regex(r"^smode_default:\d+$"))(smode_default)
app.on_callback_query(filters.regex(r"^smode_sort:\d+$"))(smode_sort)
app.on_callback_query(filters.regex(r"^smode_rarity:[^:]+:\d+$"))(smode_rarity)
app.on_callback_query(filters.regex(r"^smode_close:\d+$"))(smode_close)

# Register the new member handler for setting default droptime
app.add_handler(ChatMemberUpdatedHandler(handle_new_member))

# Filter to exclude commands
non_command_filter = filters.group & ~filters.regex(r"^/")

# Register message handler with non-command filter
app.on_message((filters.text | filters.media) & non_command_filter & command_filter)(check_message_count)

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
