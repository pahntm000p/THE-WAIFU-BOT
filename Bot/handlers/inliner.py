import re
from telegram import InlineQueryResultPhoto
from telegram.ext import InlineQueryHandler, ContextTypes
from Bot.database import db

async def get_character_details(image_id):
    character = await db.Characters.find_one({"id": image_id})
    return character

def extract_name(user_name):
    match = re.search(r'>(.*?)<', user_name)
    return match.group(1) if match else "Unknown User"

async def get_icaption_preference(user_id):
    preference = await db.Preference.find_one({"user_id": user_id})
    return preference.get("icaption", "Caption 1") if preference else "Caption 1"

async def inline_query(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    results = []

    if query.startswith("smashed."):
        owner_user_id = int(query.split(".")[1])
        user_collection = await db.Collection.find_one({"user_id": owner_user_id})

        if user_collection and user_collection.get("images"):
            user_name = extract_name(user_collection.get("user_name", "Unknown User"))  # Fetch and extract the owner's name
            user_id = user_collection["user_id"]  # Get user ID from the collection
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
            # Check if query matches a character name
            character = await db.Characters.find_one({"name": {"$regex": query, "$options": "i"}})
            if character:
                caption = (
                    f"✨ <b>Name</b><b>:</b> <b>{character['name']}</b>\n"
                    f"{character['rarity_sign']} <b>Rarity</b><b>:</b> <b>{character['rarity']}</b>\n"
                    f"🍁 <b>Anime</b><b>:</b> <b>{character['anime']}</b>\n\n"
                    f"🆔<b>:</b> <b>{character['id']}</b>"
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
            # Fetch all characters from the database if query is empty
            characters = await db.Characters.find().to_list(length=100)  # Adjust the length as needed

            for character in characters:
                caption = (
                    f"✨ <b>Name</b><b>:</b> <b>{character['name']}</b>\n"
                    f"{character['rarity_sign']} <b>Rarity</b><b>:</b> <b>{character['rarity']}</b>\n"
                    f"🍁 <b>Anime</b><b>:</b> <b>{character['anime']}</b>\n\n"
                    f"🆔<b>:</b> <b>{character['id']}</b>"
                )
                result = InlineQueryResultPhoto(
                    id=character["id"],
                    photo_url=character["img_url"],
                    thumbnail_url=character["img_url"],
                    caption=caption,
                    parse_mode='HTML'
                )
                results.append(result)

    await update.inline_query.answer(results, cache_time=1)

# Inline query handler for pbot
inline_query_handler = InlineQueryHandler(inline_query)
