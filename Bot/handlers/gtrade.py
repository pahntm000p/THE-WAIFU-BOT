from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from ..database import db
import asyncio

# Store pending global trades
pending_gtrades = {}

# Store message IDs separately for the requester and receivers
trade_message_ids = {}

# Lock for handling trades to ensure atomicity
gtrade_lock = asyncio.Lock()

async def get_character_details(image_id):
    return await db.Characters.find_one({"id": image_id})

async def get_user_collection(user_id):
    return await db.Collection.find_one({"user_id": user_id})

async def update_user_collection(user_id, updated_images):
    await db.Collection.update_one(
        {"user_id": user_id},
        {"$set": {"images": updated_images}},
        upsert=True
    )

async def update_gtrade_user(user_id, enable):
    if enable:
        await db.Gtusers.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id}},
            upsert=True
        )
    else:
        await db.Gtusers.delete_one({"user_id": user_id})

async def is_gtrade_user(user_id):
    return await db.Gtusers.find_one({"user_id": user_id}) is not None

async def get_all_gtrade_users():
    return await db.Gtusers.find({}).to_list(length=None)

async def gtrade_toggle(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /gtrade on/off/enable/disable")
        return

    command = message.command[1].lower()
    is_enabled = await is_gtrade_user(message.from_user.id)
    
    if command in ["on", "enable"]:
        if is_enabled:
            await message.reply("Global trade requests are already enabled.")
        else:
            await update_gtrade_user(message.from_user.id, True)
            await message.reply("Global trade requests enabled.")
    elif command in ["off", "disable"]:
        if not is_enabled:
            await message.reply("Global trade requests are already disabled.")
        else:
            await update_gtrade_user(message.from_user.id, False)
            await message.reply("Global trade requests disabled.")
    else:
        await message.reply("Usage: /gtrade on/off/enable/disable")

async def initiate_gtrade(client: Client, message: Message):
    if len(message.command) != 3:
        await message.reply("Usage: /gtreq {Your Character ID} {Requested Character ID}")
        return

    char_a_id = message.command[1]
    char_b_id = message.command[2]
    user_a = message.from_user

    if char_a_id == char_b_id:
        await message.reply("You cannot trade the same character with itself.")
        return

    if user_a.id in pending_gtrades:
        await message.reply("You have already initiated a global trade. Please confirm or cancel it before starting a new one.")
        return

    # Fetch user A's collection
    user_a_collection = await get_user_collection(user_a.id)

    if not user_a_collection or not any(img['image_id'] == char_a_id for img in user_a_collection.get('images', [])):
        await message.reply("You don't have the specified character to trade.")
        return

    char_a = await get_character_details(char_a_id)
    char_b = await get_character_details(char_b_id)

    if not char_a or not char_b:
        await message.reply("One of the characters doesn't exist.")
        return

    # Get all users who have enabled global trade requests
    gtrade_users = await get_all_gtrade_users()

    # Limit the number of users to 15
    limited_gtrade_users = gtrade_users[:15]
    gtrade_count = len(limited_gtrade_users)

    # Save the global trade information
    pending_gtrades[user_a.id] = {"char_a_id": char_a_id, "char_b_id": char_b_id}
    trade_message_ids[user_a.id] = {"requester_msg_id": None, "receivers_msg_ids": []}

    # Send the global trade request to limited users who enabled it
    for gtrade_user in limited_gtrade_users:
        user_b_id = gtrade_user["user_id"]
        if user_b_id == user_a.id:
            continue

        # Fetch character B details for the recipient
        char_b_recipient = await get_character_details(char_b_id)

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Accept", callback_data=f"accept_gtrade|{user_a.id}|{char_a_id}|{char_b_id}"),
             InlineKeyboardButton("Decline", callback_data=f"decline_gtrade|{user_a.id}")]
        ])

        msg = await client.send_photo(
            user_b_id,
            char_b_recipient['img_url'],
            caption=f"ℹ** {user_a.mention} has globally requested to trade : **\n\n"
                    f"✨ **Name** **:** **{char_a.get('name', 'Unknown Character')}**\n"
                    f"🍁 **Anime** **:** **{char_a.get('anime', 'Unknown Anime')}**\n"
                    f"🆔 **:** **{char_a_id}**\n\n"
                    f"**----WITH----**\n\n"
                    f"✨ **Name** **:** **{char_b.get('name', 'Unknown Character')}**\n"
                    f"🍁 **Anime** **:** **{char_b.get('anime', 'Unknown Anime')}**\n"
                    f"🆔 **:** **{char_b_id}**",
            reply_markup=buttons
        )
        trade_message_ids[user_a.id]["receivers_msg_ids"].append(msg.id)

    requester_msg = await message.reply(
        f"Your request to trade {char_a.get('name', 'Unknown Character')} with {char_b.get('name', 'Unknown Character')} has been sent to {gtrade_count} users.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel Trade", callback_data=f"cancel_gtrade|{user_a.id}")]])
    )
    trade_message_ids[user_a.id]["requester_msg_id"] = requester_msg.id

    

async def handle_gtrade_callback(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split("|")
    if len(data) < 2:
        await callback_query.answer("Invalid trade data.", show_alert=True)
        return

    action = data[0]
    user_a_id = int(data[1])

    # Fetch trade details
    trade_details = pending_gtrades.get(user_a_id, None)
    if not trade_details:
        await callback_query.answer("This trade request is no longer valid.", show_alert=True)
        return

    char_a_id = trade_details["char_a_id"]
    char_b_id = trade_details["char_b_id"]
    user_b_id = callback_query.from_user.id

    if action == "cancel_gtrade":
        if callback_query.from_user.id == user_a_id:
            del pending_gtrades[user_a_id]
            await callback_query.edit_message_text("Global Trade Canceled.")
        else:
            await callback_query.answer("You are not allowed to perform this action.", show_alert=True)

    elif action == "decline_gtrade":
        await callback_query.edit_message_text("Trade request declined.")

    elif action == "accept_gtrade":
        async with gtrade_lock:
            # Check if the trade is still valid
            if user_a_id not in pending_gtrades:
                await callback_query.edit_message_text("This trade has been accepted by someone else.")
                return

            # Fetch user collections
            user_a_collection = await get_user_collection(user_a_id)
            user_b_collection = await get_user_collection(user_b_id)

            # Ensure user B has the requested character
            if not user_b_collection or not any(img['image_id'] == char_b_id for img in user_b_collection.get('images', [])):
                await callback_query.edit_message_text("You don't have the requested character.")
                return

            # Update user A's collection
            for img in user_a_collection["images"]:
                if img["image_id"] == char_a_id:
                    if img["count"] > 1:
                        img["count"] -= 1
                    else:
                        user_a_collection["images"].remove(img)
                    break

            # Update user B's collection
            for img in user_b_collection["images"]:
                if img["image_id"] == char_b_id:
                    if img["count"] > 1:
                        img["count"] -= 1
                    else:
                        user_b_collection["images"].remove(img)
                    break

            # Add character A to user B's collection
            found = False
            for img in user_b_collection["images"]:
                if img["image_id"] == char_a_id:
                    img["count"] += 1
                    found = True
                    break
            if not found:
                user_b_collection["images"].append({"image_id": char_a_id, "count": 1})

            # Add character B to user A's collection
            found = False
            for img in user_a_collection["images"]:
                if img["image_id"] == char_b_id:
                    img["count"] += 1
                    found = True
                    break
            if not found:
                user_a_collection["images"].append({"image_id": char_b_id, "count": 1})

            # Update the collections in the database
            await update_user_collection(user_a_id, user_a_collection["images"])
            await update_user_collection(user_b_id, user_b_collection["images"])

            del pending_gtrades[user_a_id]
            user_a = await client.get_users(user_a_id)
            user_b = await client.get_users(user_b_id)
            char_a_details = await get_character_details(char_a_id)
            char_b_details = await get_character_details(char_b_id)

            trade_message = (
                f"Global Trade Completed: {user_a.mention} traded {char_a_details.get('name', 'Unknown Character')} for "
                f"{user_b.mention}'s {char_b_details.get('name', 'Unknown Character')}."
            )

            # Edit the message sent to the requester
            requester_msg_id = trade_message_ids[user_a_id]["requester_msg_id"]
            await client.edit_message_text(
                user_a_id,
                requester_msg_id,
                f"Hey, your trade request has been accepted by {user_b.mention}."
            )

            # Edit the message sent to the acceptor
            receiver_msg_id = callback_query.message.id
            await client.edit_message_text(
                user_b_id,
                receiver_msg_id,
                f"Successfully traded {char_b_details.get('name', 'Unknown Character')} with {user_a.mention}."
            )

    else:
        await callback_query.answer("Invalid action.", show_alert=True)
