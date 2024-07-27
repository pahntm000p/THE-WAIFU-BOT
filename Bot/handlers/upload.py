from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from Bot.database import db, get_next_id
from datetime import datetime, timedelta
import re
from Bot.config import SUPPORT_CHAT_ID
from pyrogram.enums import ParseMode
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
    await callback_query.message.edit_text("Upload cancelled.")

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
        sent = await message.reply(
            "Please send the anime name.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload")]]
            )
        )
        upload_data[user_id]["last_message_id"] = sent.id
    elif step == 3:
        upload_data[user_id]["anime"] = message.text.replace("-", " ")
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
    first_name = callback_query.from_user.first_name
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

async def finalize_upload(client: Client, chat_id: int, user_id: int , first_name:str):
    data = upload_data[user_id]
    try:
        new_id = await get_next_id()
        expiry = data.get("expiry")

        character = {
            "id": f"{new_id:02}",
            "img_url": data["img_url"],
            "name": data["name"],
            "anime": data["anime"],
            "rarity": RARITY_MAPPING[data["rarity"]]["name"],
            "rarity_sign": RARITY_MAPPING[data["rarity"]]["sign"],
            "expiry_time": expiry
        }

        await db.Characters.insert_one(character)
        expiry_message = f" for {expiry}" if expiry else ""

        user_mention = f"<a href='tg://user?id={user_id}'>{first_name}</a>"
        caption = (f"{user_mention} just uploaded a new character !!\n\n"
                   f"**🐼 Name --> {data['name']}  | 🌺 Anime --> {data['anime']}\n"
                   f"{RARITY_MAPPING[data['rarity']]['sign']} Rarity --> {RARITY_MAPPING[data['rarity']]['name']}  | 🪪 Id --> {new_id:02}**{expiry_message}")

        await client.send_photo(
            SUPPORT_CHAT_ID, 
            data["img_url"], 
            caption=caption, 
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

    edit_data[message.from_user.id] = {"char_id": char_id, "old_character": character}
    sent = await message.reply(
        "Which field would you like to edit?",
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
    edit_data[message.from_user.id]["last_message_id"] = sent.id

async def cancel_edit(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in edit_data:
        await client.delete_messages(callback_query.message.chat.id, edit_data[user_id]["last_message_id"])
        del edit_data[user_id]
    await callback_query.message.edit_text("Edit cancelled.")

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
            "anime": "Please provide the new Anime."
        }
        sent = await callback_query.message.reply(
            field_prompt[field],
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]
            )
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
        updates["anime"] = value.replace("-", " ")

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

        user_mention = f"<a href='tg://user?id={user_id}'>{user_id}</a>"
        for field, new_value in updates.items():
            old_value = old_character.get(field)
            if field == "img_url":
                await client.send_photo(
                    SUPPORT_CHAT_ID,
                    new_value,
                    caption=f"{user_mention} just updated the image of character with ID {char_id}",
                    parse_mode=ParseMode.HTML
                )
            else:
                await client.send_message(
                    SUPPORT_CHAT_ID,
                    f"{user_mention} just edited the {field} of character with ID {char_id} from {old_value} to {new_value}.",
                    parse_mode=ParseMode.HTML
                )
    except Exception as e:
        await client.send_message(chat_id, f"An error occurred: {e}")
    finally:
        if user_id in edit_data:
            del edit_data[user_id]
