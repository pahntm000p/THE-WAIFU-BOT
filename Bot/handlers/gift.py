from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from ..database import db

# Store pending gifts to ensure a user can only initiate one gift at a time
pending_gifts = {}

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

async def gift_character(client: Client, message: Message):
    if len(message.command) != 2:
        await message.reply("Usage: /gift {id}, reply to the user you want to gift.")
        return

    image_id = message.command[1]
    from_user_id = message.from_user.id
    to_user_id = message.reply_to_message.from_user.id if message.reply_to_message else None

    if not to_user_id:
        await message.reply("You need to reply to the user you want to gift.")
        return

    if to_user_id == from_user_id:
        await message.reply("You cannot gift a character to yourself.")
        return

    if message.reply_to_message.from_user.is_bot:
        await message.reply("You cannot gift a character to a bot.")
        return

    if from_user_id in pending_gifts:
        await message.reply("You have already initiated a gift. Please confirm or cancel it before starting a new one.")
        return

    # Fetch from_user's collection
    from_user_collection = await get_user_collection(from_user_id)

    if not from_user_collection or not any(img['image_id'] == image_id for img in from_user_collection.get('images', [])):
        await message.reply("You don't have this character in your collection.")
        return

    character = await get_character_details(image_id)
    if not character:
        await message.reply("Character not found.")
        return

    # Send confirmation message with inline buttons
    confirm_button = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Confirm",
                    callback_data=f"confirm_gift|{from_user_id}|{to_user_id}|{image_id}"
                ),
                InlineKeyboardButton(
                    "Cancel",
                    callback_data=f"cancel_gift|{from_user_id}"
                )
            ]
        ]
    )

    pending_gifts[from_user_id] = True

    await message.reply(
        f"ℹ️ Are you sure you want to gift:\n"
        f"☘️ **Name**: {character['name']}\n"
        f"to {message.reply_to_message.from_user.mention}?",
        reply_markup=confirm_button
    )

async def confirm_gift(client: Client, callback_query: CallbackQuery):
    _, from_user_id, to_user_id, image_id = callback_query.data.split("|")
    from_user_id, to_user_id = int(from_user_id), int(to_user_id)

    if callback_query.from_user.id != from_user_id:
        await callback_query.answer("You are not allowed to confirm this gift.", show_alert=True)
        return

    # Fetch both users' collections
    from_user_collection = await get_user_collection(from_user_id)
    to_user_collection = await get_user_collection(to_user_id)

    # Remove the character from the from_user's collection
    updated_from_images = []
    for img in from_user_collection.get("images", []):
        if img["image_id"] == image_id:
            if img["count"] > 1:
                img["count"] -= 1
                updated_from_images.append(img)
            else:
                continue
        else:
            updated_from_images.append(img)
    await update_user_collection(from_user_id, updated_from_images)

    # Add the character to the to_user's collection
    if to_user_collection:
        to_user_images = to_user_collection.get("images", [])
        existing_image = next((img for img in to_user_images if img["image_id"] == image_id), None)
        if existing_image:
            existing_image["count"] += 1
        else:
            to_user_images.append({"image_id": image_id, "count": 1})
    else:
        to_user_images = [{"image_id": image_id, "count": 1}]

    await update_user_collection(to_user_id, to_user_images)

    from_user_mention = (await client.get_users(from_user_id)).mention
    to_user_mention = (await client.get_users(to_user_id)).mention
    character = await get_character_details(image_id)
    
    await callback_query.edit_message_text(f"{from_user_mention} gifted {character['name']} to {to_user_mention}!")

    # Remove from pending gifts
    if from_user_id in pending_gifts:
        del pending_gifts[from_user_id]

async def cancel_gift(client: Client, callback_query: CallbackQuery):
    _, from_user_id = callback_query.data.split("|")
    from_user_id = int(from_user_id)

    if callback_query.from_user.id != from_user_id:
        await callback_query.answer("You are not allowed to cancel this gift.", show_alert=True)
        return

    await callback_query.edit_message_text("Gift cancelled.")

    # Remove from pending gifts
    if from_user_id in pending_gifts:
        del pending_gifts[from_user_id]
