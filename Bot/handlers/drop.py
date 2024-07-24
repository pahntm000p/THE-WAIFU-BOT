import random
from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus  # Import ChatMemberStatus
from ..database import get_random_image, update_drop, get_message_count, update_message_count, is_user_sudo
from ..config import OWNER_ID  # Import OWNER_ID from config.py
import requests
from io import BytesIO
import asyncio

lock = asyncio.Lock()

async def handle_new_member(client: Client, member_update: ChatMemberUpdated):
    if member_update.new_chat_member.user.is_self:
        group_id = member_update.chat.id
        await update_message_count(group_id, 100, 0)
        await client.send_message(group_id, "Default droptime set to 100 messages.")

async def is_admin_or_special(client: Client, chat_id: int, user_id: int) -> bool:
    # Check if the user is the owner of the bot or a sudo user
    if user_id == OWNER_ID or await is_user_sudo(user_id):
        return True
    
    # Otherwise, check if the user is an admin in the group
    member = await client.get_chat_member(chat_id, user_id)
    return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

async def droptime(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Please provide a message count.")
        return

    try:
        msg_count = int(message.command[1])
    except ValueError:
        await message.reply("Please provide a valid number for message count.")
        return

    group_id = message.chat.id
    user_id = message.from_user.id

    # Check if the user is authorized to change the droptime
    if not await is_admin_or_special(client, group_id, user_id):
        await message.reply("You don't have rights to change the droptime in this chat")
        return

    # Restrict non-sudo users from setting droptime below 100
    if msg_count < 100 and user_id != OWNER_ID and not await is_user_sudo(user_id):
        await message.reply("Droptime cannot be set to less than 100.")
        return

    await update_message_count(group_id, msg_count, 0)
    await message.reply(f"Random image will be dropped every {msg_count} messages in this group.")

async def check_message_count(client: Client, message: Message):
    group_id = message.chat.id
    async with lock:
        count_doc = await get_message_count(group_id)

        if count_doc:
            current_count = count_doc["current_count"] + 1
            msg_count = count_doc["msg_count"]

            if current_count >= msg_count:
                current_count = 0
                # Get a random image URL from the database
                image_doc = await get_random_image()
                if not image_doc:
                    await client.send_message(group_id, "No images available to drop.")
                    return

                image_id = image_doc["id"]
                image_url = image_doc["img_url"]
                image_name = image_doc["name"]

                try:
                    response = requests.get(image_url)
                    response.raise_for_status()

                    image_data = BytesIO(response.content)
                    image_data.name = image_url.split("/")[-1]

                    # Store the last dropped image information
                    await update_drop(group_id, image_id, image_name, image_url)

                    # Send the image with the caption
                    caption = f"O-Nee Chan ! New Character Is Here.\n**Smash her using** : /smash name"
                    await client.send_photo(group_id, image_data, caption=caption)
                except requests.exceptions.RequestException as e:
                    await client.send_message(group_id, f"Failed to download the image: {e}")

            await update_message_count(group_id, msg_count, current_count)
