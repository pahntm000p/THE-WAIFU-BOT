from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated
from ..database import update_msg_count, set_droptime, get_droptime, get_random_image, update_last_dropped_image

async def droptime(client: Client, message: Message):
    try:
        msg_count = int(message.command[1])
        chat_id = message.chat.id
        await set_droptime(chat_id, msg_count)
        await message.reply(f"Image drop time set to {msg_count} messages.")
    except (IndexError, ValueError):
        await message.reply("Usage: /droptime {msg_count}")

async def check_message_count(client: Client, message: Message):
    chat_id = message.chat.id
    msg_count = await update_msg_count(chat_id)
    droptime = await get_droptime(chat_id)

    if msg_count >= droptime:
        character = await get_random_image()
        if character and isinstance(character, dict):
            await client.send_photo(chat_id, character["img_url"])
            await update_last_dropped_image(chat_id, character)
        else:
            print("No character found or character is not a dictionary")
        await update_msg_count(chat_id, reset=True)  # Reset count after sending image

async def handle_new_chat(client: Client, chat_member_updated: ChatMemberUpdated):
    if chat_member_updated.new_chat_member:
        chat_id = chat_member_updated.chat.id
        await client.send_message(chat_id, "I will drop images every 100 messages. Use /droptime {msg_count} to change the interval.")
        await set_droptime(chat_id, 100)
        await update_msg_count(chat_id, reset=True)
