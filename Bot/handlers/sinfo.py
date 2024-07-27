from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from ..database import get_user_collection, db
from ..config import OWNER_ID as BOT_OWNER
from datetime import datetime

async def sinfo(client: Client, message: Message):
    if message.from_user.id != BOT_OWNER:
        await message.reply("You are not authorized to use this command.")
        return

    if len(message.command) > 1:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply("Please provide a valid user ID.")
            return
    elif message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        await message.reply("Please provide a user ID or reply to a user's message.")
        return

    try:
        user = await client.get_users(user_id)
        user_collection = await get_user_collection(user_id)

        total_characters = sum(image["count"] for image in user_collection["images"]) if user_collection else 0


        recent_characters = ""
        if user_collection:
            images = user_collection.get("images", [])
            # Sort images by the most recent claims (you may need a timestamp or order field for accurate sorting)
            sorted_images = sorted(images, key=lambda x: x["image_id"], reverse=True)[:5]
            for img in sorted_images:
                image_id = img["image_id"]
                count = img["count"]
                character_details = await db.Characters.find_one({"id": image_id})  # Assuming you have a Characters collection
                if character_details:
                    recent_characters += f"{character_details['name']} ({character_details['rarity']}) | x{count} .\n"
        else:
            recent_characters = "No characters smashed."

        response_text = (
            f"⟶⟶⟶⟶⟶**User Info**⟵⟵⟵⟵⟵\n"
            f"**Name**: {user.first_name}\n"
            f"**Username**: @{user.username}\n"
            f"**User ID**: {user.id}\n\n"
            f"**Character Stats**\n"
            f"**Total Characters**: {total_characters}\n\n"
            f"**| Recent Characters |**\n"
            f"{recent_characters}"
        )

        buttons = [
            [InlineKeyboardButton("Delete His Collection", callback_data=f"delete_collection_{user_id}")],
            [InlineKeyboardButton("Close", callback_data="close_sinfo")]
        ]

        await message.reply(response_text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await message.reply(f"An error occurred: {e}")

async def delete_collection(client: Client, callback_query: CallbackQuery):
    if callback_query.from_user.id != BOT_OWNER:
        await callback_query.answer("You are not authorized to perform this action.", show_alert=True)
        return

    try:
        user_id = int(callback_query.data.split("_")[2])
        await db.Collection.delete_one({"user_id": user_id})

        await callback_query.answer("User's collection has been deleted.", show_alert=True)
        await callback_query.message.delete()
    except Exception as e:
        await callback_query.answer(f"An error occurred: {e}", show_alert=True)

async def close_sinfo(client: Client, callback_query: CallbackQuery):
    if callback_query.from_user.id != BOT_OWNER:
        await callback_query.answer("You are not authorized to perform this action.", show_alert=True)
        return

    try:
        await callback_query.message.delete()
    except Exception as e:
        await callback_query.answer(f"An error occurred: {e}", show_alert=True)

