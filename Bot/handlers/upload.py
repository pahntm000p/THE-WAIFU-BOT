from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from datetime import datetime, timedelta
from Bot.database import db, get_next_id, is_user_sudo
from Bot.config import SUPPORT_CHAT_ID , OWNER_ID
import re

RARITY_MAPPING = {
    "1": {"name": "Common", "sign": "⚪️"},
    "2": {"name": "Rare", "sign": "🟠"},
    "3": {"name": "Legendary", "sign": "🟡"},
    "4": {"name": "Medium", "sign": "🟢"},
    "5": {"name": "Limited Time", "sign": "🔴"}
}

upload_data = {}
edit_data = {}

async def start_upload(client: Client, message: Message):
    upload_data[message.from_user.id] = {}
    sent = await message.reply(
        "Please send the image URL.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload")]]
        )
    )
    upload_data[message.from_user.id]["last_message_id"] = sent.id

async def cancel_upload(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in upload_data:
        await client.delete_messages(callback_query.message.chat.id, upload_data[user_id]["last_message_id"])
        del upload_data[user_id]

async def process_upload_step(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in upload_data:
        return

    step = len(upload_data[user_id])
    if step == 1:
        upload_data[user_id]["img_url"] = message.text
        await client.delete_messages(message.chat.id, upload_data[user_id]["last_message_id"])
        sent = await message.reply(
            "Please send the character name.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload")]]
            )
        )
        upload_data[user_id]["last_message_id"] = sent.id
    elif step == 2:
        upload_data[user_id]["name"] = message.text.replace("-", " ")
        await client.delete_messages(message.chat.id, upload_data[user_id]["last_message_id"])
        search_button = InlineKeyboardButton("Search for Anime", switch_inline_query_current_chat=".anime ")
        sent = await message.reply(
            "Please send the anime ID or use the button below to search for the anime.",
            reply_markup=InlineKeyboardMarkup(
                [[search_button], [InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload")]]
            )
        )
        upload_data[user_id]["last_message_id"] = sent.id
    elif step == 3:
        anime_id_text = message.text.strip()
        anime_id = None
        try:
            # Check if the text contains the formatted anime info
            if "🆔:" in anime_id_text:
                # Use regex to extract the numeric ID
                match = re.search(r'🆔:\s*(\d+)', anime_id_text)
                if match:
                    anime_id = match.group(1)
                else:
                    raise ValueError("Invalid anime ID format.")
            else:
                # Assume the text is directly the anime ID
                anime_id = anime_id_text

            anime_id = int(anime_id)
        except (ValueError, AttributeError):
            search_button = InlineKeyboardButton("Search for Anime", switch_inline_query_current_chat=".anime ")
            sent = await message.reply(
                "Invalid anime ID. Please provide a valid anime ID. If you have just created a new anime space then try searching again.",
                reply_markup=InlineKeyboardMarkup(
                    [[search_button], [InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload")]]
                )
            )
            upload_data[user_id]["last_message_id"] = sent.id
            return

        anime = await db.Anime.find_one({"anime_id": anime_id})
        if not anime:
            sent = await message.reply(
                "Invalid anime ID. Please provide a valid anime ID.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload")]]
                )
            )
            upload_data[user_id]["last_message_id"] = sent.id
            return

        upload_data[user_id]["anime"] = anime["name"]
        upload_data[user_id]["anime_id"] = anime_id
        await client.delete_messages(message.chat.id, upload_data[user_id]["last_message_id"])
        sent = await message.reply(
            "Please choose the rarity.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(f"{info['sign']} {info['name']}", callback_data=f"set_rarity_{key}")]
                    for key, info in RARITY_MAPPING.items()
                ] + [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload")]]
            )
        )
        upload_data[user_id]["last_message_id"] = sent.id
    elif step == 4:
        await client.delete_messages(message.chat.id, upload_data[user_id]["last_message_id"])
        rarity = upload_data[user_id]["rarity"]
        if rarity == "5":
            try:
                num_days = int(message.text)
            except ValueError:
                sent = await message.reply(
                    "Invalid number of days. Please provide a valid integer.",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload")]]
                    )
                )
                upload_data[user_id]["last_message_id"] = sent.id
                return
            upload_data[user_id]["expiry"] = datetime.utcnow() + timedelta(days=num_days)
        await finalize_upload(client, message.chat.id, user_id)

async def set_rarity(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in upload_data:
        rarity = callback_query.data.split("_")[-1]
        upload_data[user_id]["rarity"] = rarity
        await client.delete_messages(callback_query.message.chat.id, upload_data[user_id]["last_message_id"])
        if rarity == "5":
            sent = await callback_query.message.edit_text(
                "Please provide the number of days for Limited Time rarity.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload")]]
                )
            )
            upload_data[user_id]["last_message_id"] = sent.id
        else:
            await finalize_upload(client, callback_query.message.chat.id, user_id)


async def finalize_upload(client: Client, chat_id: int, user_id: int):
    data = upload_data[user_id]
    try:
        new_id = await get_next_id()
        expiry = data.get("expiry")

        character = {
            "id": f"{new_id:02}",
            "img_url": data["img_url"],
            "name": data["name"],
            "anime": data["anime"],
            "anime_id": data["anime_id"],
            "rarity": RARITY_MAPPING[data["rarity"]]["name"],
            "rarity_sign": RARITY_MAPPING[data["rarity"]]["sign"],
            "expiry_time": expiry
        }

        await db.Characters.insert_one(character)
        expiry_message = f" for {expiry}" if expiry else ""

        user = await client.get_users(user_id)
        user_mention = f"<a href='tg://user?id={user_id}'>{user.first_name}</a>"
        caption = (f"<b>{user_mention} just uploaded a new character !!</b>\n\n"
                   f"<b>🐼 Name : {data['name']}</b>\n"
                   f"<b>🌺 Anime : {data['anime']}</b>\n"
                   f"<b>{RARITY_MAPPING[data['rarity']]['sign']} Rarity : {RARITY_MAPPING[data['rarity']]['name']}</b>\n\n"
                   f"<b>🪪  : {new_id:02} {expiry_message}</b>")

        await client.send_photo(
            SUPPORT_CHAT_ID, 
            data["img_url"], 
            caption=caption, 
            parse_mode=ParseMode.HTML
        )

        await client.send_message(
            chat_id,
            f"<b>Character {data['name']} added successfully with ID {new_id:02} as {RARITY_MAPPING[data['rarity']]['name']} {RARITY_MAPPING[data['rarity']]['sign']}{expiry_message}.</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await client.send_message(chat_id, f"An error occurred: {e}")
    finally:
        del upload_data[user_id]



async def start_edit(client: Client, message: Message):
    params = message.text.split()
    if len(params) < 2:
        await message.reply("Usage: /edit {id}")
        return
    char_id = params[1]
    if not re.match(r"^\d+$", char_id):
        await message.reply("Character ID must be a numeric value.")
        return
    
    character = await db.Characters.find_one({"id": char_id})
    if not character:
        await message.reply(f"No character found with ID {char_id}.")
        return

    # Prepare the caption with character details
    caption = (
        f"🐼 Name: {character.get('name', 'Unknown')}\n"
        f"🌺 Anime: {character.get('anime', 'Unknown')}\n"
        f"{character.get('rarity_sign', '❓')} Rarity: {character.get('rarity', 'Unknown')}\n"
        f"🪪 ID: {char_id}\n\n"
        "Select the field you want to edit:"
    )

    # Send the message with character details and inline buttons
    sent = await message.reply_photo(
        photo=character.get('img_url', ''),
        caption=caption,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Image URL", callback_data="edit_field_img_url")],
                [InlineKeyboardButton("Name", callback_data="edit_field_name")],
                [InlineKeyboardButton("Anime", callback_data="edit_field_anime")],
                [InlineKeyboardButton("Rarity", callback_data="edit_field_rarity")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]
            ]
        )
    )

    # Store necessary information in edit_data
    edit_data[message.from_user.id] = {
        "char_id": char_id,
        "old_character": character,
        "last_message_id": sent.id
    }

async def cancel_edit(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in edit_data:
        await client.delete_messages(callback_query.message.chat.id, edit_data[user_id]["last_message_id"])
        del edit_data[user_id]

async def select_field(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    field = callback_query.data.split("_")[-1]
    edit_data[user_id]["field"] = field

    await client.delete_messages(callback_query.message.chat.id, edit_data[user_id]["last_message_id"])

    if field == "rarity":
        sent = await callback_query.message.reply(
            "Please choose the new rarity.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(f"{info['sign']} {info['name']}", callback_data=f"set_edit_rarity_{key}")]
                    for key, info in RARITY_MAPPING.items()
                ] + [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]
            )
        )
    else:
        field_prompt = {
            "img_url": "Please provide the new Image URL.",
            "name": "Please provide the new Name.",
            "anime": "Please provide the new Anime ID or use the button below to search for the anime."
        }
        search_button = InlineKeyboardButton("Search for Anime", switch_inline_query_current_chat=".anime ") if field == "anime" else None
        buttons = [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]
        if search_button:
            buttons.insert(0, [search_button])
        sent = await callback_query.message.reply(
            field_prompt[field],
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    edit_data[user_id]["last_message_id"] = sent.id

async def process_edit_step(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in edit_data:
        return

    field = edit_data[user_id]["field"]
    value = message.text.strip()

    await client.delete_messages(message.chat.id, edit_data[user_id]["last_message_id"])

    updates = {}
    if field == "img_url":
        if not re.match(r"^https?://", value):
            sent = await message.reply(
                "Invalid URL format. Please provide a valid image URL.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]
                )
            )
            edit_data[user_id]["last_message_id"] = sent.id
            return
        updates["img_url"] = value
    elif field == "name":
        updates["name"] = value.replace("-", " ")
    elif field == "anime":
        anime_id_text = value
        anime_id = None
        try:
            # Check if the text contains the formatted anime info
            if "🆔:" in anime_id_text:
                # Use regex to extract the numeric ID
                match = re.search(r'🆔:\s*(\d+)', anime_id_text)
                if match:
                    anime_id = match.group(1)
                else:
                    raise ValueError("Invalid anime ID format.")
            else:
                # Assume the text is directly the anime ID
                anime_id = anime_id_text

            anime_id = int(anime_id)
        except (ValueError, AttributeError) as e:
            sent = await message.reply(
                f"Invalid anime ID. Please provide a valid anime ID. Error: {e}",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]
                )
            )
            edit_data[user_id]["last_message_id"] = sent.id
            return

        anime = await db.Anime.find_one({"anime_id": anime_id})
        if not anime:
            sent = await message.reply(
                "Invalid anime ID. Please provide a valid anime ID.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]
                )
            )
            edit_data[user_id]["last_message_id"] = sent.id
            return

        updates["anime"] = anime["name"]
        updates["anime_id"] = anime_id

    edit_data[user_id]["updates"] = updates
    await finalize_edit(client, message.chat.id, user_id)

async def set_edit_rarity(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    rarity = callback_query.data.split("_")[-1]
    edit_data[user_id]["updates"] = {
        "rarity": RARITY_MAPPING[rarity]["name"],
        "rarity_sign": RARITY_MAPPING[rarity]["sign"]
    }
    await client.delete_messages(callback_query.message.chat.id, edit_data[user_id]["last_message_id"])
    await finalize_edit(client, callback_query.message.chat.id, user_id)

async def finalize_edit(client: Client, chat_id: int, user_id: int):
    try:
        updates = edit_data[user_id]["updates"]
        char_id = edit_data[user_id]["char_id"]
        old_character = edit_data[user_id]["old_character"]

        await db.Characters.update_one({"id": char_id}, {"$set": updates})
        await client.send_message(chat_id, f"Character with ID {char_id} updated successfully.")

        user = await client.get_users(user_id)
        user_mention = f"<a href='tg://user?id={user_id}'>{user.first_name}</a>"

        if "rarity" in updates:
            old_rarity_sign = old_character['rarity_sign']
            old_rarity = old_character['rarity']
            new_rarity_sign = updates['rarity_sign']
            new_rarity = updates['rarity']
            await client.send_photo(
                SUPPORT_CHAT_ID,
                old_character['img_url'],
                caption=(
                    f"<b>{user_mention} has just updated the rarity of {old_character['name']} from:</b>\n\n"
                    f"<b>{old_rarity_sign} {old_rarity} to {new_rarity_sign} {new_rarity}</b>"
                ),
                parse_mode=ParseMode.HTML
            )
        else:
            for field, new_value in updates.items():
                old_value = old_character.get(field)
                if field == "img_url":
                    await client.send_photo(
                        SUPPORT_CHAT_ID,
                        new_value,
                        caption=f"<b>{user_mention} just updated the image of character with ID {char_id}</b>",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await client.send_photo(
                        SUPPORT_CHAT_ID,
                        old_character['img_url'],
                        caption=(
                            f"<b>{user_mention} just edited the {field} of character with ID {char_id} from {old_value} to {new_value}.</b>"
                        ),
                        parse_mode=ParseMode.HTML
                    )
    except Exception as e:
        await client.send_message(chat_id, f"An error occurred: {e}")
    finally:
        if user_id in edit_data:
            del edit_data[user_id]




async def delete_character(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID and not await is_user_sudo(user_id):
        await message.reply_text("🚫 This command is restricted to the bot owner and sudo users.")
        return
    
    params = message.text.split()
    if len(params) < 2:
        await message.reply("Usage: /delete {id}")
        return
    
    char_id = params[1]
    if not re.match(r"^\d+$", char_id):
        await message.reply("Character ID must be a numeric value.")
        return
    
    character = await db.Characters.find_one({"id": char_id})
    if not character:
        await message.reply(f"No character found with ID {char_id}.")
        return

    # Log the deletion in the support chat
    user = await client.get_users(user_id)
    user_mention = f"<a href='tg://user?id={user_id}'>{user.first_name}</a>"
    await client.send_photo(
        SUPPORT_CHAT_ID,
        character.get('img_url', ''),
        caption=f"<b>{user_mention} deleted the character:</b>\n\n"
                f"🐼 Name: {character.get('name', 'Unknown')}\n"
                f"🌺 Anime: {character.get('anime', 'Unknown')}\n"
                f"{character.get('rarity_sign', '❓')} Rarity: {character.get('rarity', 'Unknown')}\n"
                f"🪪 ID: {char_id}",
        parse_mode=ParseMode.HTML
    )
    
    # Delete the character
    await db.Characters.delete_one({"id": char_id})
    await message.reply_text(f"Character with ID {char_id} deleted successfully.")

def add_delete_handler(app: Client):
    @app.on_message(filters.command("delete"))
    async def handle_delete(client: Client, message: Message):
        await delete_character(client, message)

