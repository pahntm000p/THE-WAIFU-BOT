import time
import random
from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus
from ..database import update_drop, get_message_count, update_message_count, is_user_sudo, ban_user, is_user_banned, get_all_images
from ..config import OWNER_ID, SUPPORT_CHAT_ID
import requests
from io import BytesIO
import asyncio

lock = asyncio.Lock()
message_timestamps = {}  # Dictionary to store user message timestamps
ban_durations = {}  # Dictionary to store user ban durations

# Function to reset ban durations after a certain period of good behavior
async def reset_ban_duration(user_id):
    await asyncio.sleep(3600)  # 1 hour
    ban_durations[user_id] = 10  # Reset ban duration to 10 minutes

async def handle_new_member(client: Client, member_update: ChatMemberUpdated):
    if member_update.new_chat_member.user.is_self and (not member_update.old_chat_member or member_update.old_chat_member.status == "left"):
        group_id = member_update.chat.id
        group_title = member_update.chat.title
        group_username = f"@{member_update.chat.username}" if member_update.chat.username else "N/A"
        added_by_username = member_update.from_user.username if member_update.from_user.username else "N/A"
        added_by_first_name = member_update.from_user.first_name
        members_count = await client.get_chat_members_count(group_id)

        await update_message_count(group_id, 100, 0)
        await client.send_message(group_id, "**Random waifus will be dropped every 100 messages here !!**")

        await client.send_message(
            SUPPORT_CHAT_ID,
            f"🏠 **Added To New Group**\n\n"
            f"🆔 **Group ID:** `{group_id}`\n"
            f"📛 **Group Name:** {group_title}\n"
            f"✳ **Group Username:** {group_username}\n"
            f"👤 **Added By:** `{added_by_first_name}`\n"
            f"🔗 **Username:** @{added_by_username}\n"
            f"📊 **Members Count:** `{members_count}`"
        )

async def is_admin_or_special(client: Client, chat_id: int, user_id: int) -> bool:
    if user_id == OWNER_ID or await is_user_sudo(user_id):
        return True
    
    member = await client.get_chat_member(chat_id, user_id)
    return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

async def droptime(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("⚠️ **Please provide a message count.**")
        return

    try:
        msg_count = int(message.command[1])
    except ValueError:
        await message.reply("🚫 **Please provide a valid number for the message count.**")
        return

    group_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin_or_special(client, group_id, user_id):
        await message.reply("🚫 **You don't have the rights to change the droptime in this chat.**")
        return

    if msg_count < 100 and user_id != OWNER_ID and not await is_user_sudo(user_id):
        await message.reply("⚠️ **Droptime cannot be set to less than 100 messages.**")
        return

    await update_message_count(group_id, msg_count, 0)
    await message.reply(f"🎉 **Random waifus will be dropped every {msg_count} messages in this group.**")

async def check_message_count(client: Client, message: Message):
    user_id = message.from_user.id
    group_id = message.chat.id
    current_time = time.time()

    if await is_user_banned(user_id):
        return

    async with lock:
        if user_id not in message_timestamps:
            message_timestamps[user_id] = []

        # Add current message timestamp
        message_timestamps[user_id].append(current_time)

        # Clean up old timestamps beyond the threshold window (2 seconds)
        message_timestamps[user_id] = [timestamp for timestamp in message_timestamps[user_id] if current_time - timestamp <= 2]

        if len(message_timestamps[user_id]) >= 5:
            # Ban the user
            if user_id not in ban_durations:
                ban_durations[user_id] = 10  # Initial ban duration is 10 minutes
            else:
                ban_durations[user_id] *= 2  # Double the ban duration for repeated offenses

            await ban_user(user_id, ban_durations[user_id])  # Ban user for the current duration
            await client.send_message(group_id, f"🚫 **User {message.from_user.first_name} has been temporarily banned for {ban_durations[user_id]} minutes due to spamming.**")

            # Schedule a reset for the ban duration after an hour
            asyncio.create_task(reset_ban_duration(user_id))
            return

        count_doc = await get_message_count(group_id)

        if count_doc:
            current_count = count_doc["current_count"] + 1
            msg_count = count_doc["msg_count"]

            if current_count >= msg_count:
                current_count = 0

                # Fetch all available images and shuffle them
                all_images = await get_all_images()
                if not all_images:
                    print("Lol..No Characters Uploaded")
                    return

                random.shuffle(all_images)
                character = all_images[0]  # Pick the first character after shuffling

                character_id = character["id"]
                character_url = character["img_url"]
                character_name = character["name"]

                try:
                    response = requests.get(character_url)
                    response.raise_for_status()

                    image_data = BytesIO(response.content)
                    image_data.name = character_url.split("/")[-1]

                    # Send the photo and capture the message response
                    photo_message = await client.send_photo(group_id, image_data, caption=f"O-Nee Chan ! New Waifu Is Here.\nSmash her using : /smash name")

                    # Construct the message link
                    chat_id = photo_message.chat.id
                    message_id = photo_message.id
                    message_link = f"https://t.me/c/{str(chat_id)[4:]}/{message_id}"

                    # Update the drop with the message link
                    await update_drop(group_id, character_id, character_name, character_url, message_link)

                except requests.exceptions.RequestException as e:
                    await client.send_message(group_id, f"Failed to download the image: {e}")

            await update_message_count(group_id, msg_count, current_count)

