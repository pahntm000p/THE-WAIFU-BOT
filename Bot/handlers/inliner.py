import re
from aiogram.types import InlineQuery, InlineQueryResultPhoto
from Bot.database import db

async def get_character_details(image_id):
    character = await db.Characters.find_one({"id": image_id})
    return character

def extract_name(user_name):
    match = re.search(r'>(.*?)<', user_name)
    return match.group(1) if match else "Unknown User"

async def inline_query_handler(inline_query: InlineQuery):
    query = inline_query.query
    results = []

    if query.startswith("smashed."):
        user_id = int(query.split(".")[1])
        user_collection = await db.Collection.find_one({"user_id": user_id})

        if user_collection and user_collection.get("images"):
            user_name = extract_name(user_collection.get("user_name", "Unknown User"))  # Fetch and extract the owner's name
            for image in user_collection["images"]:
                character = await get_character_details(image["image_id"])
                if character:
                    result = InlineQueryResultPhoto(
                        id=character["id"],
                        photo_url=character["img_url"],
                        thumbnail_url=character["img_url"],
                        caption=(
                            f"<b>Look at {user_name}'s smashed character !!</b>\n\n"
                            f"✨<b>Name :</b> <b>{character['name']}</b>\n"
                            f"{character['rarity_sign']} <b>Rarity :</b> <b>{character['rarity']}</b>\n"
                            f"🍁<b>Anime :</b> <b>{character['anime']}</b>\n\n"
                            f"🆔 : <b>{character['id']}</b>"
                        ),
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
                result = InlineQueryResultPhoto(
                    id=character["id"],
                    photo_url=character["img_url"],
                    thumbnail_url=character["img_url"],
                    caption=(
                        f"✨ <b>Name</b><b>:</b> <b>{character['name']}</b>\n"
                        f"{character['rarity_sign']} <b>Rarity</b><b>:</b> <b>{character['rarity']}</b>\n"
                        f"🍁 <b>Anime</b><b>:</b> <b>{character['anime']}</b>\n\n"
                        f"🆔<b>:</b> <b>{character['id']}</b>"
                    ),
                    parse_mode='HTML'
                )
                results.append(result)
        else:
            # Fetch all characters from the database if query is empty
            characters = await db.Characters.find().to_list(length=100)  # Adjust the length as needed

            for character in characters:
                result = InlineQueryResultPhoto(
                    id=character["id"],
                    photo_url=character["img_url"],
                    thumbnail_url=character["img_url"],
                    caption=(
                        f"✨ <b>Name</b><b>:</b> <b>{character['name']}</b>\n"
                        f"{character['rarity_sign']} <b>Rarity</b><b>:</b> <b>{character['rarity']}</b>\n"
                        f"🍁 <b>Anime</b><b>:</b> <b>{character['anime']}</b>\n\n"
                        f"🆔<b>:</b> <b>{character['id']}</b>"
                    ),
                    parse_mode='HTML'
                )
                results.append(result)

    await inline_query.answer(results, cache_time=1)
