from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from datetime import datetime
from Bot.database import db, is_user_sudo
from telegraph import Telegraph
import re
from ..config import SUPPORT_CHAT_ID

# New Rarity Mapping
RARITY_MAPPING_GEN2 = {
    "1": {"name": "Mythical", "sign": "🦄"},
    "2": {"name": "Divine", "sign": "👼"},
    "3": {"name": "Elite", "sign": "🔱"},
    "4": {"name": "Epic", "sign": "💎"},
    "5": {"name": "Exotic", "sign": "🍹"},
    "6": {"name": "Ultimate", "sign": "👑"}
}

gen2_upload_data = {}

telegraph = Telegraph()
telegraph.create_account(short_name='WaifuBot')

# Function to generate the next Gen2 ID (AAA, AAB, etc.)
async def get_next_gen2_id():
    counter = await db.Counters.find_one_and_update(
        {"_id": "gen2_character_id"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    sequence_value = counter["sequence_value"]
    # Convert sequence_value to a string in AAA format
    next_id = ""
    while sequence_value > 0:
        sequence_value -= 1
        next_id = chr((sequence_value % 26) + 65) + next_id
        sequence_value //= 26
    return next_id.rjust(3, 'A')

async def start_gen2_upload(client: Client, message: Message):
    gen2_upload_data[message.from_user.id] = {}
    sent = await message.reply(
        "🖼️ Please send the image for Gen2 character.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_gen2_upload")]]
        )
    )
    gen2_upload_data[message.from_user.id]["last_message_id"] = sent.id

async def cancel_gen2_upload(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in gen2_upload_data:
        await client.delete_messages(callback_query.message.chat.id, gen2_upload_data[user_id]["last_message_id"])
        del gen2_upload_data[user_id]

async def process_gen2_upload_step(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in gen2_upload_data:
        return

    step = len(gen2_upload_data[user_id])
    if step == 1 and message.photo:
        file_id = message.photo.file_id
        file_path = await client.download_media(file_id)
        response = telegraph.upload_file(file_path)
        img_url = f"https://telegra.ph{response[0]['src']}"
        gen2_upload_data[user_id]["img_url"] = img_url
        await client.delete_messages(message.chat.id, gen2_upload_data[user_id]["last_message_id"])
        sent = await message.reply(
            "📝 Please send the character name.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_gen2_upload")]]
            )
        )
        gen2_upload_data[user_id]["last_message_id"] = sent.id

    elif step == 2:
        gen2_upload_data[user_id]["name"] = message.text.replace("-", " ")
        await client.delete_messages(message.chat.id, gen2_upload_data[user_id]["last_message_id"])
        search_button = InlineKeyboardButton("🔍 Search for Anime", switch_inline_query_current_chat=".anime ")
        sent = await message.reply(
            "📺 Please send the anime ID or use the button below to search for the anime.",
            reply_markup=InlineKeyboardMarkup(
                [[search_button], [InlineKeyboardButton("❌ Cancel", callback_data="cancel_gen2_upload")]]
            )
        )
        gen2_upload_data[user_id]["last_message_id"] = sent.id

    elif step == 3:
        anime_id_text = message.text.strip()
        anime_id = None
        try:
            if "🆔:" in anime_id_text:
                match = re.search(r'🆔:\s*(\d+)', anime_id_text)
                if match:
                    anime_id = match.group(1)
                else:
                    raise ValueError("Invalid anime ID format.")
            else:
                anime_id = anime_id_text
            anime_id = int(anime_id)
        except (ValueError, AttributeError):
            search_button = InlineKeyboardButton("🔍 Search for Anime", switch_inline_query_current_chat=".anime ")
            sent = await message.reply(
                "❗ Invalid anime ID. Please provide a valid anime ID. If you have just created a new anime space then try searching again.",
                reply_markup=InlineKeyboardMarkup(
                    [[search_button], [InlineKeyboardButton("❌ Cancel", callback_data="cancel_gen2_upload")]]
                )
            )
            gen2_upload_data[user_id]["last_message_id"] = sent.id
            return

        anime = await db.Anime.find_one({"anime_id": anime_id})
        if not anime:
            sent = await message.reply(
                "❗ Invalid anime ID. Please provide a valid anime ID.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_gen2_upload")]]
                )
            )
            gen2_upload_data[user_id]["last_message_id"] = sent.id
            return

        gen2_upload_data[user_id]["anime"] = anime["name"]
        gen2_upload_data[user_id]["anime_id"] = anime_id
        await client.delete_messages(message.chat.id, gen2_upload_data[user_id]["last_message_id"])
        sent = await message.reply(
            "🌟 Please choose the rarity.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(f"{info['sign']} {info['name']}", callback_data=f"set_gen2_rarity_{key}")]
                    for key, info in RARITY_MAPPING_GEN2.items()
                ] + [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_gen2_upload")]]
            )
        )
        gen2_upload_data[user_id]["last_message_id"] = sent.id

async def set_gen2_rarity(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in gen2_upload_data:
        rarity = callback_query.data.split("_")[-1]
        gen2_upload_data[user_id]["rarity"] = rarity
        await client.delete_messages(callback_query.message.chat.id, gen2_upload_data[user_id]["last_message_id"])
        await finalize_gen2_upload(client, callback_query.message.chat.id, user_id)

async def finalize_gen2_upload(client: Client, chat_id: int, user_id: int):
    data = gen2_upload_data[user_id]
    try:
        new_id = await get_next_gen2_id()

        character = {
            "id": new_id,
            "img_url": data["img_url"],
            "name": data["name"],
            "anime": data["anime"],
            "anime_id": data["anime_id"],
            "rarity": RARITY_MAPPING_GEN2[data["rarity"]]["name"],
            "rarity_sign": RARITY_MAPPING_GEN2[data["rarity"]]["sign"],
            "level": 0  # Initial level is 0
        }

        await db.Gen2Chara.insert_one(character)

        user = await client.get_users(user_id)
        user_mention = f"<a href='tg://user?id={user_id}'>{user.first_name}</a>"
        caption = (f"🌟 <b>New Gen2 Character Alert!</b> 🌟\n\n"
           f"🎉 <b>{user_mention} has just uploaded:</b>\n\n"
           f"🆔 <b>ID:</b> <code>{new_id}</code>\n"
           f"💥 <b>Name:</b> <i>{data['name']}</i>\n"
           f"🎌 <b>Anime:</b> <i>{data['anime']}</i>\n"
           f"🔮 <b>Rarity:</b> {RARITY_MAPPING_GEN2[data['rarity']]['sign']} <i>{RARITY_MAPPING_GEN2[data['rarity']]['name']}</i>")


        await client.send_photo(
            SUPPORT_CHAT_ID,
            data["img_url"],
            caption=caption,
            parse_mode=ParseMode.HTML
        )

        await client.send_message(
            chat_id,
            f"<b>Gen2 Character {data['name']} added successfully with ID {new_id} as {RARITY_MAPPING_GEN2[data['rarity']]['name']} {RARITY_MAPPING_GEN2[data['rarity']]['sign']}.</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await client.send_message(chat_id, f"❗ An error occurred: {e}")
    finally:
        del gen2_upload_data[user_id]
