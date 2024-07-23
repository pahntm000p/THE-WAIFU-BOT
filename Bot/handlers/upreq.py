import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Bot.database import db, get_next_id
from Bot.config import SUPPORT_CHAT_ID, OWNER_ID
from Bot.database import is_user_sudo
from bson.objectid import ObjectId

# Mapping for rarity
RARITY_MAPPING = {
    "1": {"name": "Common", "sign": "⚪️"},
    "2": {"name": "Rare", "sign": "🟣"},
    "3": {"name": "Legendary", "sign": "🟡"},
    "4": {"name": "Medium", "sign": "🟢"},
}

async def upreq(client: Client, message: Message):
    try:
        user_id = message.from_user.id
        params = message.text.split()
        if len(params) != 5:
            await message.reply("Usage: /upreq {img_url} {name} {anime} {rarity}")
            return

        _, img_url, name, anime, rarity = params

        if rarity not in RARITY_MAPPING:
            await message.reply("Invalid rarity. Please use 1, 2, 3, or 4.")
            return

        # Check the user's request count for the day
        today = datetime.utcnow().date()
        request_count = await db.Upreq.count_documents({"user_id": user_id, "date": today.isoformat()})
        if request_count >= 3:
            await message.reply("You can only request up to 3 characters per day.")
            return

        # Create the new request document
        rarity_info = RARITY_MAPPING[rarity]
        request = {
            "user_id": user_id,
            "img_url": img_url,
            "name": name.replace("-", " "),
            "anime": anime.replace("-", " "),
            "rarity": rarity_info["name"],
            "rarity_sign": rarity_info["sign"],
            "date": today.isoformat(),
            "status": "Pending"
        }
        result = await db.Upreq.insert_one(request)
        request_id = str(result.inserted_id)

        # Send the image to the support chat
        caption = (f"✨ **Name** **:** {request['name']}\n"
                   f"{request['rarity_sign']} **Rarity** **:** **{request['rarity']}**\n"
                   f"🍁 **Anime** **:** **{request['anime']}**")

        buttons = [
            [InlineKeyboardButton("Approve", callback_data=f"approve_upreq:{request_id}"),
             InlineKeyboardButton("Decline", callback_data=f"decline_upreq:{request_id}")]
        ]
        await client.send_photo(
            SUPPORT_CHAT_ID,
            img_url,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        await message.reply("Your request has been sent to the support team.")

    except Exception as e:
        await message.reply(f"An error occurred: {e}")

async def handle_callback(client: Client, callback_query):
    try:
        data = callback_query.data.split(':')
        action = data[0]
        request_id = data[1]

        request = await db.Upreq.find_one({"_id": ObjectId(request_id)})

        if not request:
            await callback_query.answer("Request not found.", show_alert=True)
            return

        if action == "approve_upreq":
            if callback_query.from_user.id == OWNER_ID or await is_user_sudo(callback_query.from_user.id):
                # Generate a new unique ID for the character
                new_id = await get_next_id()

                # Create the new character document
                character = {
                    "id": f"{new_id:02}",
                    "img_url": request['img_url'],
                    "name": request['name'],
                    "anime": request['anime'],
                    "rarity": request['rarity'],
                    "rarity_sign": request['rarity_sign']
                }

                # Insert the character into the database
                await db.Characters.insert_one(character)
                caption = (f"✨ **Name** **:** {request['name']}\n"
                           f"{request['rarity_sign']} **Rarity** **:** **{request['rarity']}**\n"
                           f"🍁 **Anime** **:** **{request['anime']}**\n"
                           "✅ **Status:** Approved")
                await callback_query.message.edit_caption(caption)
                await db.Upreq.update_one({"_id": ObjectId(request_id)}, {"$set": {"status": "Approved"}})
                await callback_query.answer("Request approved and character added successfully.")
            else:
                await callback_query.answer("You are not authorized to approve this request.", show_alert=True)

        elif action == "decline_upreq":
            if callback_query.from_user.id == OWNER_ID or await is_user_sudo(callback_query.from_user.id):
                caption = (f"✨ **Name** **:** {request['name']}\n"
                           f"{request['rarity_sign']} **Rarity** **:** **{request['rarity']}**\n"
                           f"🍁 **Anime** **:** **{request['anime']}**\n"
                           "❌ **Status:** Declined")
                await callback_query.message.edit_caption(caption)
                await db.Upreq.update_one({"_id": ObjectId(request_id)}, {"$set": {"status": "Declined"}})
                await callback_query.answer("Request declined.")
            else:
                await callback_query.answer("You are not authorized to decline this request.", show_alert=True)

    except Exception as e:
        await callback_query.answer(f"An error occurred: {e}", show_alert=True)
