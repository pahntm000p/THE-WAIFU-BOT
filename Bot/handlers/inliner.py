import re
import base64
import struct
from telegram import InlineQueryResultPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import InlineQueryHandler, CallbackQueryHandler, ContextTypes
from Bot.database import db
from telegram.constants import ParseMode
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineQueryResultPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from ..database import get_next_anime_id

async def get_character_details(character_id):
    character = await db.Characters.find_one({"id": character_id})
    return character

async def fetch_user_name(bot, user_id):
    user = await bot.get_chat(user_id)
    mention = f"{user.first_name}"
    return mention


async def get_icaption_preference(user_id):
    preference = await db.Preference.find_one({"user_id": user_id})
    return preference.get("icaption", "Caption 1") if preference else "Caption 1"

def extract_chat_id(inline_message_id: str) -> int:
    decoded_id = base64.urlsafe_b64decode(inline_message_id + "=" * (4 - len(inline_message_id) % 4))
    dc_id, message_id, chat_id, query_id = struct.unpack("<iiiq", decoded_id)
    if chat_id < 0:
        chat_id = int(f"-100{abs(chat_id)}")
    return chat_id

async def fetch_user_names(bot, user_ids):
    users = await bot.get_chat_members(user_ids)
    return {user.user.id: user.user.mention for user in users}

async def handle_search_anime(query, results):
    anime_name = query.split("search.anime ", 1)[1]
    animes = await db.Anime.find({"name": {"$regex": anime_name, "$options": "i"}}).to_list(length=100)

    for anime in animes:
        character_count = await db.Characters.count_documents({"anime_id": anime["anime_id"]})

        caption = (
            f"✨ <b>Anime</b><b>:</b> <b>{anime['name']}</b>\n"
            f"🆔<b>:</b> <b>{anime['anime_id']}</b>\n\n"
            f"<b>Characters uploaded:</b> {character_count}"
        )

        result = InlineQueryResultArticle(
            id=str(anime["anime_id"]),
            title=anime["name"],
            input_message_content=InputTextMessageContent(caption, parse_mode='HTML')
        )
        results.append(result)

async def handle_anime_query(query, results):
    anime_name = query.split(".anime ", 1)[1]
    animes = await db.Anime.find({"name": {"$regex": anime_name, "$options": "i"}}).to_list(length=100)
    
    if animes:
        for anime in animes:
            caption = (
                f"✨ <b>Anime</b><b>:</b> <b>{anime['name']}</b>\n"
                f"🆔<b>:</b> <b>{anime['anime_id']}</b>"
            )
            result = InlineQueryResultArticle(
                id=str(anime["anime_id"]),
                title=anime["name"],
                input_message_content=InputTextMessageContent(caption, parse_mode='HTML')
            )
            results.append(result)
    else:
        # If no anime is found, provide an option to create a new one
        caption = f"No anime found with the name '{anime_name}'. Click below to create it."
        create_anime_caption = (
            f"Anime '{anime_name}' has been created successfully."
        )

        result = InlineQueryResultArticle(
            id="create_anime",
            title=f"Create Anime: {anime_name}",
            input_message_content=InputTextMessageContent(caption, parse_mode='HTML'),
            description="Click here to create a new anime",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Create Anime", callback_data=f"create_anime:{anime_name}")
            ]])
        )
        results.append(result)

async def create_anime_callback(update, context):
    query = update.callback_query
    anime_name = query.data.split(":")[1]

    # Check if the anime already exists
    existing_anime = await db.Anime.find_one({"name": anime_name})
    if existing_anime:
        await query.answer(f"Anime '{anime_name}' already exists with ID {existing_anime['anime_id']}.")
        return

    # Create the new anime
    anime_id = await get_next_anime_id()
    await db.Anime.insert_one({"name": anime_name, "anime_id": anime_id})
    
    await query.answer(f"Anime '{anime_name}' has been created successfully with ID {anime_id}.")
    await query.edit_message_text(
        f"Anime '{anime_name}' has been created successfully with ID {anime_id}.",
        parse_mode='HTML'
    )

async def inline_query(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    results = []

    if query.startswith("smashed."):
        parts = query.split(" ", 1)
        try:
            owner_user_id = int(parts[0].split(".")[1])
            search_term = parts[1] if len(parts) > 1 else ""
        except (IndexError, ValueError):
            owner_user_id = None
            search_term = ""

        if owner_user_id is not None:
            user_collection = await db.Collection.find_one({"user_id": owner_user_id})

            if user_collection and user_collection.get("images"):
                user_name = await fetch_user_name(context.bot, user_collection["user_id"])
                user_id = user_collection["user_id"]
                icaption_preference = await get_icaption_preference(user_id)

                anime_character_count = {}
                for image in user_collection["images"]:
                    character = await get_character_details(image["image_id"])
                    if character:
                        anime_id = character["anime_id"]
                        if (anime_id not in anime_character_count):
                            anime_character_count[anime_id] = 0
                        anime_character_count[anime_id] += 1

                matching_images = []
                for image in user_collection["images"]:
                    character = await get_character_details(image["image_id"])
                    if character:
                        if search_term.isdigit() and character["id"] == int(search_term):
                            matching_images.append(image)
                        elif re.search(search_term, character["name"], re.IGNORECASE):
                            matching_images.append(image)

                for image in matching_images:
                    character = await get_character_details(image["image_id"])
                    if character:
                        total_uploaded_characters = await db.Characters.count_documents({"anime_id": character["anime_id"]})
                        user_character_count = anime_character_count[character["anime_id"]]

                        if icaption_preference == "Caption 1":
                            caption = (
                                f"<b>╔═════ ∘◦ ✾ ◦∘ ═════╗</b>\n"
                                f"<b>   {user_name}'s {character['rarity']} Smash</b>\n"
                                f"<b>╚═════ ∘◦ ❈ ◦∘ ═════╝</b>\n\n"
                                f"<b>🍒 Name </b> <b>≿ {character['name']} (x{image['count']}) ≾</b>\n"
                                f"<b>🎴 Anime </b> <b>⊱ {character['anime']} ({user_character_count}/{total_uploaded_characters}) ⊰</b>\n"
                                f"<b>{character['rarity_sign']} Rarity:</b> <b> {character['rarity']} </b>\n\n"
                                f"<b>🔖 ID </b> <b>≼ {character['id']} ≽</b>"
                            )
                        else:
                            caption = (
                                f"🫧<b>Check out {user_name}'s Smash!</b>🫧\n\n"
                                f"➤ 🧩 <b>{character['name']}</b>  <b>x{image['count']}</b> | <b>{character['anime']}</b> ({user_character_count}/{total_uploaded_characters})\n"
                                f"➤ {character['rarity_sign']} <b><i>({character['rarity']})</i></b> | 🔖 <b>{character['id']}</b> \n"
                            )
                        result = InlineQueryResultPhoto(
                            id=str(character["id"]),
                            photo_url=character["img_url"],
                            thumbnail_url=character["img_url"],
                            caption=caption,
                            parse_mode='HTML'
                        )
                        results.append(result)


    elif query.startswith(".anime "):
        await handle_anime_query(query, results)
    elif query.startswith("search.anime "):
        await handle_search_anime(query, results)
    else:
        # Global search for characters by name or ID
        characters = []
        if query.isdigit() or re.match(r"^\d+$", query):
            # Search by numeric string ID
            characters = await db.Characters.find({"id": query}).to_list(length=100)
        else:
            # Search by name using regex
            characters = await db.Characters.find({"name": {"$regex": query, "$options": "i"}}).to_list(length=100)

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
                id=str(character["id"]),
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
        # Find the count of the specific character for this user
        image = next((img for img in smasher["images"] if img["image_id"] == character_id), None)
        count = image["count"] if image else 0
        smasher_mentions.append(f"--> <a href='tg://user?id={user.id}'>{user.first_name}</a> (x{count})")

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
create_anime_callback_handler = CallbackQueryHandler(create_anime_callback, pattern=r'^create_anime:')
