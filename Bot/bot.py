from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from pyrogram.handlers import CallbackQueryHandler, ChatMemberUpdatedHandler
from .config import OWNER_ID as BOT_OWNER , SUPPORT_CHAT_ID
from . import app, pbot
from .handlers import *
from Bot.database import db, get_next_anime_id
from .git import git_pull_command, restart_command


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


# Middleware to save user ID
async def save_user_id(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    if not await db.TotalUsers.find_one({"user_id": user_id}):
        await db.TotalUsers.insert_one({"user_id": user_id})
        log_message = (
            f"👤 **New User Started The Bot**\n\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"📛 **First Name:** `{first_name}`\n"
            f"🔗 **Username:** @{username if username else 'N/A'}"
        )
        await client.send_message(SUPPORT_CHAT_ID, log_message)

# Decorator to save user ID
def save_user_id_decorator(handler):
    async def wrapper(client: Client, message: Message):
        await save_user_id(client, message)
        await handler(client, message)
    return wrapper


# Register handlers
app.on_message(filters.command("gitpull") & filters.user(BOT_OWNER))(git_pull_command)
app.on_message(filters.command("restart") & filters.user(BOT_OWNER))(restart_command)


# Register handlers
app.on_message(filters.command("start") & filters.private & command_filter)(save_user_id_decorator(start))
app.on_message(filters.command("help") & filters.private & command_filter)(save_user_id_decorator(help))
app.on_message(filters.command("search") & command_filter)(save_user_id_decorator(search))
app.on_message(filters.command("droptime") & filters.group & command_filter)(save_user_id_decorator(droptime))
app.on_message(filters.command("smash") & filters.group & command_filter)(save_user_id_decorator(smash_image))
app.on_message(filters.command("smashes") & command_filter)(save_user_id_decorator(smashes))
app.on_message(filters.command("gift") & filters.group & filters.reply & command_filter)(save_user_id_decorator(gift_character))
app.on_message(filters.command("daan") & sudo_filter)(save_user_id_decorator(daan))
app.on_message(filters.command("sudoers") & filters.user(BOT_OWNER))(save_user_id_decorator(sudoers))
app.on_message(filters.command("sinfo") & sudo_filter)(save_user_id_decorator(sinfo))
app.on_message(filters.command("bang") & sudo_filter)(save_user_id_decorator(ban))
app.on_message(filters.command("unbang") & sudo_filter)(save_user_id_decorator(unban))
app.on_message(filters.command("sudo") & filters.user(BOT_OWNER))(save_user_id_decorator(add_sudo))
app.on_message(filters.command("rmsudo") & filters.user(BOT_OWNER))(save_user_id_decorator(remove_sudo))
app.on_message(filters.command("fav") & command_filter)(save_user_id_decorator(set_fav))
app.on_message(filters.command("unfav") & command_filter)(save_user_id_decorator(unfav))
app.on_message(filters.command("smode") & command_filter)(save_user_id_decorator(smode))
app.on_message(filters.command("top") & filters.group & command_filter)(save_user_id_decorator(top))
app.on_message(filters.command("gtop") & command_filter)(gtop)
app.on_message(filters.command("check") & filters.group & command_filter)(check_character)
app.on_message(filters.command("sstatus") & command_filter)(sstatus)
app.on_message(filters.command("cmode") & command_filter)(set_cmode)
app.on_message(filters.command("ctop") & filters.group & command_filter)(ctop)
app.on_message(filters.command("tdtop") & filters.group & command_filter)(tdtop)
app.on_callback_query(filters.regex(r"^cmode_select:\d+:") & command_filter)(cmode_select)
app.on_callback_query(filters.regex(r"^cmode_close:\d+$") & command_filter)(cmode_close)
app.on_message(filters.command("claim"))(claim_handler)
app.on_message(filters.command("setfsub") & filters.private)(set_force_sub)
app.on_message(filters.command("managegrpids") & filters.private)(manage_group_ids)
app.on_message(filters.command("broadcast") & filters.reply & filters.user(BOT_OWNER))(handle_broadcast)
app.on_message(filters.command("transfer") & filters.user(BOT_OWNER))(transfer_collection)
add_eval_handlers(app)
add_ping_handler(app)
add_delete_handler(app)  # Add the delete handler
add_callback_query_handlers(app)
add_logs_handler(app)  # Add the logs handler
app.on_message(filters.command("sanime") & sudo_filter)(search_anime)

# Gtrade
app.on_message(filters.command("gtreq") & filters.private & command_filter)(gtrade_toggle)
app.on_message(filters.command("gtrade") & filters.private & command_filter)(initiate_gtrade)
app.on_callback_query(filters.regex(r"^accept_gtrade\|"))(handle_gtrade_callback)
app.on_callback_query(filters.regex(r"^decline_gtrade\|"))(handle_gtrade_callback)
app.on_callback_query(filters.regex(r"^cancel_gtrade\|"))(handle_gtrade_callback)

# Register the command and callback handlers
app.on_message(filters.command("trade") & filters.reply & filters.group & command_filter)(initiate_trade)
app.on_callback_query(filters.regex(r"^(confirm_trade|cancel_trade|cancel_last_trade)\|") & command_filter)(handle_trade_callback)
app.add_handler(CallbackQueryHandler(confirm_gift, filters.regex(r"^confirm_gift\|") & command_filter))
app.add_handler(CallbackQueryHandler(cancel_gift, filters.regex(r"^cancel_gift\|") & command_filter))
app.add_handler(CallbackQueryHandler(cancel_last_gift, filters.regex(r"^cancel_last_gift\|") & command_filter))
app.add_handler(CallbackQueryHandler(delete_collection, filters.regex(r"^delete_collection_") & command_filter))
app.add_handler(CallbackQueryHandler(close_sinfo, filters.regex(r"^close_sinfo") & command_filter))
app.on_callback_query(filters.regex(r"^fav_confirm:\d+:\d+$"))(fav_confirm)
app.on_callback_query(filters.regex(r"^fav_cancel:\d+$"))(fav_cancel)
app.on_callback_query(filters.regex(r"^smode_default:\d+$"))(smode_default)
app.on_callback_query(filters.regex(r"^smode_sort:\d+$"))(smode_sort)
app.on_callback_query(filters.regex(r"^smode_rarity:[^:]+:\d+$"))(smode_rarity)
app.on_callback_query(filters.regex(r"^smode_close:\d+$"))(smode_close)
app.add_handler(CallbackQueryHandler(show_smashers, filters.regex(r"^show_smashers_")))
app.add_handler(CallbackQueryHandler(paginate_collection, filters.regex(r"^page_(\d+)_(\d+)$")))

# Register the new member handler for setting default droptime
app.add_handler(ChatMemberUpdatedHandler(handle_new_member))

#MSG COUNT
non_command_filter = filters.group & ~filters.regex(r"^/")
app.on_message((filters.text | filters.media | filters.sticker) & filters.group & command_filter)(check_message_count)

#Heh
# Register command handlers
@app.on_message(filters.command("backup") & filters.user(OWNER_ID))
async def backup_command(client: Client, message: Message):
    await handle_backup(client, message)

@app.on_message(filters.command("restore") & filters.user(OWNER_ID))
async def restore_command(client: Client, message: Message):
    await handle_restore(client, message)




# Upload/Edit
@app.on_message(filters.command("upload") & command_filter & sudo_filter)
async def handle_upload(client: Client, message: Message):
    await start_upload(client, message)

@app.on_callback_query(filters.regex(r"^set_rarity_") & command_filter & sudo_filter)
async def handle_set_rarity(client: Client, callback_query: CallbackQuery):
    await set_rarity(client, callback_query)

@app.on_callback_query(filters.regex(r"^cancel_upload$") & command_filter & sudo_filter)
async def handle_cancel_upload(client: Client, callback_query: CallbackQuery):
    await cancel_upload(client, callback_query)

@app.on_message(filters.command("edit") & command_filter & sudo_filter)
async def handle_edit(client: Client, message: Message):
    await start_edit(client, message)

@app.on_callback_query(filters.regex(r"^edit_field_") & command_filter & sudo_filter)
async def handle_select_field(client: Client, callback_query: CallbackQuery):
    await select_field(client, callback_query)

@app.on_callback_query(filters.regex(r"^set_edit_rarity_") & command_filter & sudo_filter)
async def handle_set_edit_rarity(client: Client, callback_query: CallbackQuery):
    await set_edit_rarity(client, callback_query)

@app.on_callback_query(filters.regex(r"^cancel_edit$") & command_filter & sudo_filter)
async def handle_cancel_edit(client: Client, callback_query: CallbackQuery):
    await cancel_edit(client, callback_query)

# Handlers
@app.on_message(filters.command("upreq") & filters.private)
async def handle_upload_request(client: Client, message: Message):
    await start_upload_request(client, message)

@app.on_callback_query(filters.regex(r"^set_request_rarity_"))
async def handle_set_request_rarity(client: Client, callback_query: CallbackQuery):
    await set_request_rarity(client, callback_query)

@app.on_callback_query(filters.regex(r"^cancel_upload_request$"))
async def handle_cancel_upload_request(client: Client, callback_query: CallbackQuery):
    await cancel_upload_request(client, callback_query)

@app.on_callback_query(filters.regex(r"^(approve_upreq|decline_upreq):"))
async def handle_approval_callback(client: Client, callback_query: CallbackQuery):
    await handle_callback(client, callback_query)

@app.on_message(filters.photo & filters.private)
async def handle_photo(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in upload_data:
        await process_upload_step(client, message)
    elif user_id in edit_data:
        await process_edit_photo(client, message)

@app.on_message(filters.text & filters.private)
async def handle_text(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id in upload_request_data:
        await process_upload_request_step(client, message)
    elif user_id in upload_data:
        await process_upload_step(client, message)
    elif user_id in edit_data:
        await process_edit_step(client, message)



def main() -> None:
    """Run bot."""
    pbot.add_handler(inline_query_handler)
    pbot.add_handler(smasher_callback_handler)
    pbot.add_handler(create_anime_callback_handler)
    pbot.run_polling(drop_pending_updates=True)


