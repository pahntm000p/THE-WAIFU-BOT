import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from Bot.database import db, get_next_id, is_user_sudo
from Bot.config import SUPPORT_CHAT_ID, OWNER_ID
from bson.objectid import ObjectId
from pyrogram.enums import ParseMode

RARITY_MAPPING = {
    "1": {"name": "Common", "sign": "⚪️"},
    "2": {"name": "Rare", "sign": "🟣"},
    "3": {"name": "Legendary", "sign": "🟡"},
    "4": {"name": "Medium", "sign": "🟢"},
}

upload_request_data = {}
upload_data = {}

async def start_upload_request(client: Client, message: Message):
    user_id = message.from_user.id
    upload_request_data[user_id] = {}
    sent = await message.reply(
        "Please send the image URL.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload_request")]]
        )
    )
    upload_request_data[user_id]["last_message_id"] = sent.id

async def cancel_upload_request(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in upload_request_data:
        await client.delete_messages(callback_query.message.chat.id, upload_request_data[user_id]["last_message_id"])
        del upload_request_data[user_id]

async def process_upload_request_step(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in upload_request_data:
        return

    step = len(upload_request_data[user_id])
    if step == 1:
        upload_request_data[user_id]["img_url"] = message.text
        await client.delete_messages(message.chat.id, upload_request_data[user_id]["last_message_id"])
        sent = await message.reply(
            "Please send the character name.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload_request")]]
            )
        )
        upload_request_data[user_id]["last_message_id"] = sent.id
    elif step == 2:
        upload_request_data[user_id]["name"] = message.text.replace("-", " ")
        await client.delete_messages(message.chat.id, upload_request_data[user_id]["last_message_id"])
        sent = await message.reply(
            "Please send the anime name.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload_request")]]
            )
        )
        upload_request_data[user_id]["last_message_id"] = sent.id
    elif step == 3:
        upload_request_data[user_id]["anime"] = message.text.replace("-", " ")
        await client.delete_messages(message.chat.id, upload_request_data[user_id]["last_message_id"])
        sent = await message.reply(
            "Please choose the rarity.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(f"{info['sign']} {info['name']}", callback_data=f"set_request_rarity_{key}")]
                    for key, info in RARITY_MAPPING.items()
                ] + [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload_request")]]
            )
        )
        upload_request_data[user_id]["last_message_id"] = sent.id

async def set_request_rarity(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in upload_request_data:
        rarity = callback_query.data.split("_")[-1]
        upload_request_data[user_id]["rarity"] = rarity
        await client.delete_messages(callback_query.message.chat.id, upload_request_data[user_id]["last_message_id"])
        await finalize_upload_request(client, callback_query.message.chat.id, user_id)

async def finalize_upload_request(client: Client, chat_id: int, user_id: int):
    data = upload_request_data[user_id]
    try:
        today = datetime.utcnow().date()
        request_count = await db.Upreq.count_documents({"user_id": user_id, "date": today.isoformat()})
        if request_count >= 3:
            await client.send_message(chat_id, "You can only request up to 3 characters per day.")
            del upload_request_data[user_id]
            return

        rarity_info = RARITY_MAPPING[data["rarity"]]
        request = {
            "user_id": user_id,
            "img_url": data["img_url"],
            "name": data["name"],
            "anime": data["anime"],
            "rarity": rarity_info["name"],
            "rarity_sign": rarity_info["sign"],
            "date": today.isoformat(),
            "status": "Pending"
        }
        result = await db.Upreq.insert_one(request)
        request_id = str(result.inserted_id)

        caption = (f"✨ **Name**: {request['name']}\n"
                   f"{request['rarity_sign']} **Rarity**: {request['rarity']}\n"
                   f"🍁 **Anime**: {request['anime']}")
        buttons = [
            [InlineKeyboardButton("Approve", callback_data=f"approve_upreq:{request_id}"),
             InlineKeyboardButton("Decline", callback_data=f"decline_upreq:{request_id}")]
        ]
        await client.send_photo(
            SUPPORT_CHAT_ID,
            data["img_url"],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        sent = await client.send_message(chat_id, "Your request has been sent to the support team.")
        upload_request_data[user_id]["last_message_id"] = sent.id
        upload_request_data[user_id]["request_message_id"] = sent.id  # Store the message ID
    except Exception as e:
        await client.send_message(chat_id, f"An error occurred: {e}")
    finally:
        del upload_request_data[user_id]

async def handle_callback(client: Client, callback_query: CallbackQuery):
    try:
        data = callback_query.data.split(':')
        action = data[0]
        request_id = data[1]

        request = await db.Upreq.find_one({"_id": ObjectId(request_id)})

        if not request:
            await callback_query.answer("Request not found.", show_alert=True)
            return

        user_id = request["user_id"]
        request_message_id = upload_request_data.get(user_id, {}).get("request_message_id")

        if action == "approve_upreq":
            if callback_query.from_user.id == OWNER_ID or await is_user_sudo(callback_query.from_user.id):
                new_id = await get_next_id()
                character = {
                    "id": f"{new_id:02}",
                    "img_url": request['img_url'],
                    "name": request['name'],
                    "anime": request['anime'],
                    "rarity": request['rarity'],
                    "rarity_sign": request['rarity_sign']
                }

                await db.Characters.insert_one(character)

                approved_caption = (f"✨ **Name**: {request['name']}\n"
                                    f"{request['rarity_sign']} **Rarity**: {request['rarity']}\n"
                                    f"🍁 **Anime**: {request['anime']}\n"
                                    "✅ **Status:** Approved")
                await callback_query.message.edit_caption(approved_caption)
                await db.Upreq.update_one({"_id": ObjectId(request_id)}, {"$set": {"status": "Approved"}})
                await callback_query.answer("Request approved and character added successfully.")

                approver = await client.get_users(callback_query.from_user.id)
                approver_mention = f"<a href='tg://user?id={approver.id}'>{approver.first_name}</a>"
                caption = (f"<b>{approver_mention} just approved the upload request !!</b>\n\n"
                           f"<b>🐼 Name : {request['name']}</b>\n"
                           f"<b>🌺 Anime : {request['anime']}</b>\n"
                           f"{request['rarity_sign']} <b>Rarity : {request['rarity']}</b>\n\n"
                           f"<b>🪪  : {new_id:02}</b>")

                await client.send_photo(
                    SUPPORT_CHAT_ID,
                    request["img_url"],
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )

                if request_message_id:
                    await client.edit_message_text(
                        chat_id=request["user_id"],
                        message_id=request_message_id,
                        text=f"Your request has been approved and the character has been added successfully by {approver_mention}.",
                        parse_mode=ParseMode.HTML
                    )
                await client.send_message(
                    chat_id=user_id,
                    text=f"Your request has been approved and the character has been added successfully by {approver_mention}.",
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback_query.answer("You are not authorized to approve this request.", show_alert=True)

        elif action == "decline_upreq":
            if callback_query.from_user.id == OWNER_ID or await is_user_sudo(callback_query.from_user.id):
                declined_caption = (f"✨ **Name**: {request['name']}\n"
                                    f"{request['rarity_sign']} **Rarity**: {request['rarity']}\n"
                                    f"🍁 **Anime**: {request['anime']}\n"
                                    "❌ **Status:** Declined")
                await callback_query.message.edit_caption(declined_caption)
                await db.Upreq.update_one({"_id": ObjectId(request_id)}, {"$set": {"status": "Declined"}})
                await callback_query.answer("Request declined.")

                decliner = await client.get_users(callback_query.from_user.id)
                decliner_mention = f"<a href='tg://user?id={decliner.id}'>{decliner.first_name}</a>"
                caption = (f"<b>{decliner_mention} just declined the upload request !!</b>\n\n"
                           f"<b>🐼 Name : {request['name']}</b>\n"
                           f"<b>🌺 Anime : {request['anime']}</b>\n"
                           f"{request['rarity_sign']} <b>Rarity : {request['rarity']}</b>")

                await client.send_photo(
                    SUPPORT_CHAT_ID,
                    request["img_url"],
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )

                if request_message_id:
                    await client.edit_message_text(
                        chat_id=request["user_id"],
                        message_id=request_message_id,
                        text=f"Your request has been declined by {decliner_mention}.",
                        parse_mode=ParseMode.HTML
                    )
                await client.send_message(
                    chat_id=user_id,
                    text=f"Your request has been declined by {decliner_mention}.",
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback_query.answer("You are not authorized to decline this request.", show_alert=True)
    except Exception as e:
        await callback_query.answer(f"An error occurred: {e}", show_alert=True)
