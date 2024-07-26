import re
import base64
import struct
from telegram import InlineQueryResultPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import InlineQueryHandler, CallbackQueryHandler, ContextTypes
from Bot.database import db
from telegram.constants import ParseMode


async def get_character_details(image_id):
    character = await db.Characters.find_one({"id": image_id})
    return character

def extract_name(user_name):
    match = re.search(r'>(.*?)<', user_name)
    return match.group(1) if match else "Unknown User"

async def get_icaption_preference(user_id):
    preference = await db.Preference.find_one({"user_id": user_id})
    return preference.get("icaption", "Caption 1") if preference else "Caption 1"

def extract_chat_id(inline_message_id: str) -> int:
    decoded_id = base64.urlsafe_b64decode(inline_message_id + "=" * (4 - len(inline_message_id) % 4))
    dc_id, message_id, chat_id, query_id = struct.unpack("<iiiq", decoded_id)
    if chat_id < 0:
        chat_id = int(f"-100{abs(chat_id)}")
    return chat_id

async def fetch_user_names(client, user_ids):
    users = await client.get_users(user_ids)
    return {user.id: user.mention for user in users}

async def inline_query(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    results = []

    if query.startswith("smashed."):
        owner_user_id = int(query.split(".")[1])
        user_collection = await db.Collection.find_one({"user_id": owner_user_id})

        if user_collection and user_collection.get("images"):
            user_name = extract_name(user_collection.get("user_name", "Unknown User"))
            user_id = user_collection["user_id"]
            icaption_preference = await get_icaption_preference(user_id)
            for image in user_collection["images"]:
                character = await get_character_details(image["image_id"])
                if character:
                    if icaption_preference == "Caption 1":
                        caption = (
                            f"<b>Look at {user_name}'s smashed character !!</b>\n\n"
                            f"✨<b>Name :</b> <b>{character['name']}</b>\n"
                            f"{character['rarity_sign']} <b>Rarity :</b> <b>{character['rarity']}</b>\n"
                            f"🍁<b>Anime :</b> <b>{character['anime']}</b>\n\n"
                            f"🆔 : <b>{character['id']}</b>"
                        )
                    else:
                        caption = (
                                   f"𝙐𝙬𝙪 , 𝘾𝙝𝙚𝙘𝙠 {user_name}’𝙨 𝘼𝙨𝙨𝙚𝙩\n\n"
                                   f"☘️ <b>{character['name']}  | {character['anime']} | x{image['count']}</b>\n"
                                   f"(<b>{character['rarity_sign']} {character['rarity']}</b>)\n"
                                  )
                    result = InlineQueryResultPhoto(
                        id=character["id"],
                        photo_url=character["img_url"],
                        thumbnail_url=character["img_url"],
                        caption=caption,
                        parse_mode='HTML'
                    )
                    results.append(result)
        else:
            pass
    else:
        if query:
            character = await db.Characters.find_one({"name": {"$regex": query, "$options": "i"}})
            if character:
                caption = (
                    f"✨ <b>Name</b><b>:</b> <b>{character['name']}</b>\n"
                    f"{character['rarity_sign']} <b>Rarity</b><b>:</b> <b>{character['rarity']}</b>\n"
                    f"🍁 <b>Anime</b><b>:</b> <b>{character['anime']}</b>\n\n"
                    f"🆔<b>:</b> <b>{character['id']}</b>"
                )
                button = InlineKeyboardButton("Smashers Here", callback_data=f"smasher:{character['id']}")
                keyboard = InlineKeyboardMarkup([[button]])
                result = InlineQueryResultPhoto(
                    id=character["id"],
                    photo_url=character["img_url"],
                    thumbnail_url=character["img_url"],
                    caption=caption,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
                results.append(result)
        else:
            characters = await db.Characters.find().to_list(length=100)
            for character in characters:
                caption = (
                    f"✨ <b>Name</b><b>:</b> <b>{character['name']}</b>\n"
                    f"{character['rarity_sign']} <b>Rarity</b><b>:</b> <b>{character['rarity']}</b>\n"
                    f"🍁 <b>Anime</b><b>:</b> <b>{character['anime']}</b>\n\n"
                    f"🆔<b>:</b> <b>{character['id']}</b>"
                )
                button = InlineKeyboardButton("Smashers Here", callback_data=f"smasher:{character['id']}")
                keyboard = InlineKeyboardMarkup([[button]])
                result = InlineQueryResultPhoto(
                    id=character["id"],
                    photo_url=character["img_url"],
                    thumbnail_url=character["img_url"],
                    caption=caption,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
                results.append(result)

    await update.inline_query.answer(results, cache_time=1)

async def smasher_callback(update, context):
    query = update.callback_query
    inline_message_id = query.inline_message_id
    character_id = query.data.split(":")[1]

    chat_id = extract_chat_id(inline_message_id)
    chat = await context.bot.get_chat(chat_id)
    chat_name = chat.title  # Fetch chat name

    character = await get_character_details(character_id)
    if not character:
        await query.answer("Character not found.")
        return

    smashers = await db.Collection.find({"images.image_id": character_id}).to_list(length=None)
    smasher_mentions = []
    for smasher in smashers:
        user = await context.bot.get_chat(smasher["user_id"])
        smasher_mentions.append(f"--> <a href='tg://user?id={user.id}'>{user.first_name}</a>")  # Fetch user full name

    smasher_text = f"<b>✨ Name: {character['name']}\n"
    smasher_text += f"🟡 Rarity: {character['rarity']}\n"
    smasher_text += f"🍁 Anime: {character['anime']}\n"
    smasher_text += f"🆔: {character['id']}\n\n"
    smasher_text += f"Smashers of {character['name']} in {chat_name} !!\n\n" + "\n".join(smasher_mentions) + "</b>"
    
    existing_caption = query.message.caption if query.message else ""
    new_caption = f"{existing_caption}\n\n{smasher_text}"

    await query.edit_message_caption(new_caption, parse_mode='HTML')




inline_query_handler = InlineQueryHandler(inline_query)
smasher_callback_handler = CallbackQueryHandler(smasher_callback, pattern=r'^smasher:')

