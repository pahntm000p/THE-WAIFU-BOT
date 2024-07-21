from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from ..database import get_user_collection, db
from ..config import OWNER_ID as BOT_OWNER

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

    user = await client.get_users(user_id)
    user_collection = await get_user_collection(user_id)

    total_characters = sum(image["count"] for image in user_collection["images"]) if user_collection else 0

    response_text = (
        f"**NAME**: {user.first_name}\n"
        f"**Total Characters**: {total_characters}"
    )

    buttons = [
        [
            InlineKeyboardButton("Delete His Collection", callback_data=f"delete_collection_{user_id}"),
            InlineKeyboardButton("Close", callback_data="close_sinfo")
        ]
    ]

    await message.reply(response_text, reply_markup=InlineKeyboardMarkup(buttons))

async def delete_collection(client: Client, callback_query):
    if callback_query.from_user.id != BOT_OWNER:
        await callback_query.answer("You are not authorized to perform this action.", show_alert=True)
        return

    user_id = int(callback_query.data.split("_")[2])
    await db.Collection.delete_one({"user_id": user_id})

    await callback_query.answer("User's collection has been deleted.", show_alert=True)
    await callback_query.message.delete()

async def close_sinfo(client: Client, callback_query):
    if callback_query.from_user.id != BOT_OWNER:
        await callback_query.answer("You are not authorized to perform this action.", show_alert=True)
        return

    await callback_query.message.delete()
