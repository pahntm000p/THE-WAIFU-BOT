from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from ..database import db
import asyncio

# Store pending trades to ensure a user can only initiate one trade at a time
pending_trades = {}

# Lock for handling trades to ensure atomicity
trade_lock = asyncio.Lock()

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

async def initiate_trade(client: Client, message: Message):
    if len(message.command) != 3:
        await message.reply("**Usage: /trade Your_Character_ID User's_Character_ID, reply to the user you want to trade with.**")
        return

    char_a_id = message.command[1]
    char_b_id = message.command[2]
    user_a = message.from_user
    user_b = message.reply_to_message.from_user if message.reply_to_message else None

    if not user_b:
        await message.reply("You need to reply to the user you want to trade with.")
        return

    if user_a.id == user_b.id or user_b.is_bot:
        await message.reply("You can't trade with yourself or bots.")
        return

    if user_a.id in pending_trades:
        await message.reply("You have already initiated a trade. Please confirm or cancel it before starting a new one.")
        return

    # Fetch user collections
    user_a_collection = await get_user_collection(user_a.id)
    user_b_collection = await get_user_collection(user_b.id)

    if not user_a_collection or not any(img['image_id'] == char_a_id for img in user_a_collection.get('images', [])):
        await message.reply("You don't have the specified character to trade.")
        return

    if not user_b_collection or not any(img['image_id'] == char_b_id for img in user_b_collection.get('images', [])):
        await message.reply("The user doesn't have the specified character to trade.")
        return

    if char_a_id == char_b_id:
        await message.reply("You can't trade the same character.")
        return

    # Fetch character details
    char_a = await get_character_details(char_a_id)
    char_b = await get_character_details(char_b_id)

    if not char_a or not char_b:
        await message.reply("One of the characters doesn't exist.")
        return

    # Save the trade information
    trade_id = f"{user_a.id}_{user_b.id}"
    pending_trades[user_a.id] = trade_id
    pending_trades[user_b.id] = trade_id

    # Send the trade request message with inline buttons
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Confirm", callback_data=f"confirm_trade|{trade_id}|{char_a_id}|{char_b_id}"),
         InlineKeyboardButton("Cancel", callback_data=f"cancel_trade|{trade_id}")]
    ])

    await message.reply(
        f"{user_a.mention} wants to trade {char_a.get('name', 'Unknown Character')} with {user_b.mention}'s {char_b.get('name', 'Unknown Character')}.",
        reply_markup=buttons
    )

async def handle_trade_callback(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split("|")
    if len(data) < 2:
        await callback_query.answer("Invalid trade data.", show_alert=True)
        return

    action = data[0]
    trade_id = data[1]

    if action == "confirm_trade" and len(data) < 4:
        await callback_query.answer("Invalid trade data.", show_alert=True)
        return

    user_a_id, user_b_id = map(int, trade_id.split("_"))

    # Ensure only the user who received the trade request can click the buttons
    if callback_query.from_user.id != user_b_id:
        await callback_query.answer("You are not allowed to perform this action.", show_alert=True)
        return

    if action == "cancel_trade":
        del pending_trades[user_a_id]
        del pending_trades[user_b_id]
        await callback_query.edit_message_text("Trade Canceled.")
    elif action == "confirm_trade":
        char_a_id = data[2]
        char_b_id = data[3]
        async with trade_lock:
            user_a_collection = await get_user_collection(user_a_id)
            user_b_collection = await get_user_collection(user_b_id)

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

            del pending_trades[user_a_id]
            del pending_trades[user_b_id]
            user_a = await client.get_users(user_a_id)
            user_b = await client.get_users(user_b_id)
            char_a_details = await get_character_details(char_a_id)
            char_b_details = await get_character_details(char_b_id)
            await callback_query.edit_message_text(f"Trade Completed: {user_a.mention} traded {char_a_details.get('name', 'Unknown Character')} for {user_b.mention}'s {char_b_details.get('name', 'Unknown Character')}.")
    else:
        await callback_query.answer("Only the user who received the trade request can confirm it.", show_alert=True)


