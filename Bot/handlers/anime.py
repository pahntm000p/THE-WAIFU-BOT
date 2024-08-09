from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters
from Bot.database import db
from ..config import OWNER_ID

ANIME_LIST_PAGE_SIZE = 10

# Check if user is sudo
async def is_user_sudo(user_id):
    return await db.Sudo.find_one({"user_id": user_id}) is not None

async def has_permission(user_id):
    return user_id == OWNER_ID or await is_user_sudo(user_id)

async def list_animes(update: Update, context):
    user_id = update.effective_user.id
    if not await has_permission(user_id):
        print("Heh")
        return

    # Get the page number from the callback data or default to the first page
    page = int(context.match.group(1)) if context.match else 1

    # Calculate the offset and limit for the current page
    offset = (page - 1) * ANIME_LIST_PAGE_SIZE
    animes = await db.Anime.find().skip(offset).limit(ANIME_LIST_PAGE_SIZE).to_list(length=ANIME_LIST_PAGE_SIZE)
    total_animes = await db.Anime.count_documents({})

    if not animes:
        await update.callback_query.edit_message_text("No animes found.")
        return

    response = f"Anime List (Page {page}):\n"
    for anime in animes:
        response += f"ID: {anime['anime_id']}, Name: {anime['name']}\n"

    # Prepare pagination buttons
    buttons = []
    if offset > 0:
        buttons.append(InlineKeyboardButton("Previous", callback_data=f"list_animes:{page-1}"))
    if offset + ANIME_LIST_PAGE_SIZE < total_animes:
        buttons.append(InlineKeyboardButton("Next", callback_data=f"list_animes:{page+1}"))

    keyboard = InlineKeyboardMarkup([buttons])

    if update.callback_query:
        await update.callback_query.edit_message_text(response, reply_markup=keyboard)
    else:
        await update.message.reply_text(response, reply_markup=keyboard)

async def rename_anime(update: Update, context):
    user_id = update.effective_user.id
    if not await has_permission(user_id):
        await update.message.reply_text("You do not have permission to perform this action.")
        return

    query = update.callback_query
    await query.answer("Please enter the anime ID and new name in the format: <anime_id> <new_name>.")
    context.user_data['rename_anime_mode'] = True
    await query.edit_message_text("Please enter the anime ID and new name in the format: <anime_id> <new_name>.")

async def rename_anime_text(update: Update, context):
    user_id = update.effective_user.id
    if not await has_permission(user_id):
        print("Heh")

        return

    if not context.user_data.get('rename_anime_mode'):
        return

    try:
        anime_id, new_anime_name = update.message.text.split(" ", 1)
        anime_id = int(anime_id)
        result_message = await rename_anime_logic(anime_id, new_anime_name)
        await update.message.reply_text(result_message)
    except ValueError:
        await update.message.reply_text("Invalid format. Please enter the anime ID and new name correctly.")
    finally:
        context.user_data['rename_anime_mode'] = False

async def rename_anime_logic(anime_id, new_anime_name):
    anime = await db.Anime.find_one({"anime_id": anime_id})
    if not anime:
        return f"No anime found with ID {anime_id}."

    await db.Anime.update_one({"anime_id": anime_id}, {"$set": {"name": new_anime_name}})
    await db.Characters.update_many({"anime_id": anime_id}, {"$set": {"anime": new_anime_name}})

    return f"Anime with ID {anime_id} has been renamed to {new_anime_name}."

async def anime_menu(update: Update, context):
    user_id = update.effective_user.id
    if not await has_permission(user_id):
        print("Heh")
        return

    keyboard = [
        [InlineKeyboardButton("List Anime", callback_data="list_animes:1")],
        [InlineKeyboardButton("Rename Anime", callback_data="rename_anime")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose the option you want !!:", reply_markup=reply_markup)

# Command and Callback Handlers
anime_menu_handler = CommandHandler("anime", anime_menu, filters=filters.ChatType.PRIVATE)
list_animes_callback_handler = CallbackQueryHandler(list_animes, pattern=r'^list_animes:(\d+)$')
rename_anime_callback_handler = CallbackQueryHandler(rename_anime, pattern=r'^rename_anime$')
rename_anime_text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, rename_anime_text)
