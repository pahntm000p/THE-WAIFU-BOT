from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from ..database import db
from .preference import get_character_details, get_fav_character, get_smode_preference
from pyrogram.enums import ParseMode

ITEMS_PER_PAGE = 5

async def smashes(client: Client, message: Message):
    user_id = message.from_user.id
    await send_collection_page(client, message, user_id, 1, new_message=True)

async def send_collection_page(client, message, user_id, page_number, new_message):
    # Fetch the user's collection
    user_collection = await db.Collection.find_one({"user_id": user_id})

    if not user_collection or not user_collection.get("images"):
        await message.reply("You don't have any smashed characters yet.")
        return

    # Fetch the favorite character if set
    fav_character_id = await get_fav_character(user_id)

    # Fetch character details for each smashed image
    smode_preference = await get_smode_preference(user_id)

    sorted_images = []
    if smode_preference == "Default":
        sorted_images = user_collection["images"]
    else:
        for image in user_collection["images"]:
            character = await get_character_details(image["image_id"])
            if character and character.get("rarity") == smode_preference:
                sorted_images.append(image)

    total_pages = (len(sorted_images) - 1) // ITEMS_PER_PAGE + 1
    start_index = (page_number - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    current_page_images = sorted_images[start_index:end_index]

    user_first_name = message.from_user.first_name
    response_text = f"<b>{user_first_name}'s Collection (Page {page_number} of {total_pages}):</b>\n\n"

    # Create a dictionary to count characters per anime and total characters uploaded for each anime
    anime_character_count = {}
    anime_total_characters = {}
    for image in user_collection["images"]:
        character = await get_character_details(image["image_id"])
        if character:
            anime_id = character["anime_id"]
            if anime_id not in anime_character_count:
                anime_character_count[anime_id] = 0
                anime_total_characters[anime_id] = await db.Characters.count_documents({"anime_id": anime_id})
            anime_character_count[anime_id] += 1

    for image in current_page_images:
        character = await get_character_details(image["image_id"])
        if character:
            anime_id = character["anime_id"]
            user_anime_count = anime_character_count[anime_id]
            total_anime_count = anime_total_characters[anime_id]
            response_text += (
                f"✨<b>{character['name']} [x{image['count']}]</b>\n"
                f"<i>{character['rarity_sign']} | {character['rarity']}</i>\n"
                f"<b>📺 {character['anime']} ({user_anime_count}/{total_anime_count})</b>\n"
                "⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋\n"
            )

    # Determine which image URL to use (favorite or first in collection)
    img_url = None
    if fav_character_id:
        fav_character = await get_character_details(fav_character_id)
        if fav_character and any(image["image_id"] == fav_character_id for image in user_collection["images"]):
            img_url = fav_character["img_url"]

    if not img_url and user_collection["images"]:
        first_character = await get_character_details(user_collection["images"][0]["image_id"])
        if first_character and "img_url" in first_character:
            img_url = first_character["img_url"]

    # Pagination buttons
    total_unique_characters = len(user_collection["images"])
    buttons = [
        [InlineKeyboardButton(f"📜 Smashes ({total_unique_characters})", switch_inline_query_current_chat=f"smashed.{user_id}")],
    ]
    if page_number < total_pages:
        buttons.append([InlineKeyboardButton("➡️ Next", callback_data=f"page_{user_id}_{page_number+1}")])
    if page_number > 1:
        buttons.append([InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{user_id}_{page_number-1}")])

    reply_markup = InlineKeyboardMarkup(buttons)

    # Send or edit the message with the user's collection as the caption
    if img_url:
        if new_message:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=img_url,
                caption=response_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
        else:
            await client.edit_message_caption(
                chat_id=message.chat.id,
                message_id=message.id,
                caption=response_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
    else:
        if new_message:
            await message.reply(response_text, reply_markup=reply_markup)
        else:
            await client.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.id,
                text=response_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )

async def paginate_collection(client: Client, callback_query):
    user_id, page_number = map(int, callback_query.data.split("_")[1:])

    if callback_query.from_user.id != user_id:
        await callback_query.answer("That's not your collection.", show_alert=True)
        return

    message = callback_query.message
    message.from_user = callback_query.from_user  # Set the correct user for the message
    await send_collection_page(client, message, user_id, page_number, new_message=False)
