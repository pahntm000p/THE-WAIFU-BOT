# Bot/handlers/inliner.py
from telegram import InlineQueryResultPhoto
from telegram.ext import InlineQueryHandler
from Bot.database import db

async def inline_query(update, context):
    query = update.inline_query.query

    if query == "":
        # Fetch all characters from the database
        characters = await db.Characters.find().to_list(length=100)  # Adjust the length as needed

        results = []
        for character in characters:
            result = InlineQueryResultPhoto(
                id=character["id"],
                photo_url=character["img_url"],
                thumbnail_url=character["img_url"],
                caption=f"✨ <b>Name</b><b>:</b> <b>{character['name']}</b>\n"
                  f"{character['rarity_sign']} <b>Rarity</b><b>:</b> <b>{character['rarity']}</b>\n"
                  f"🍁 <b>Anime</b><b>:</b> <b>{character['anime']}</b>\n\n"
                  f"🆔<b>:</b> <b>{character['id']}</b>",
                parse_mode='HTML'
            )
            results.append(result)

        await update.inline_query.answer(results, cache_time=1)

# Inline query handler for pbot
inline_query_handler = InlineQueryHandler(inline_query)
