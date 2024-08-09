import random
import time
from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus
from ..database import update_drop, get_message_count, update_message_count, is_user_sudo, ban_user, is_user_banned, get_random_character
from ..config import OWNER_ID , SUPPORT_CHAT_ID
import requests
from io import BytesIO
import asyncio
import time
from collections import defaultdict

message_timestamps = defaultdict(list)
warned_users = {}  # Dictionary to store warned users and their warning timestamp
ignore_duration = 10 * 60  # 10 minutes in seconds

lock = asyncio.Lock()

async def handle_new_member(client: Client, member_update: ChatMemberUpdated):
    # Ensure old_chat_member is not None
    if member_update.new_chat_member.user.is_self and (not member_update.old_chat_member or member_update.old_chat_member.status == "left"):
        group_id = member_update.chat.id
        group_title = member_update.chat.title
        group_username = f"@{member_update.chat.username}" if member_update.chat.username else "N/A"
        added_by_username = member_update.from_user.username if member_update.from_user.username else "N/A"
        added_by_first_name = member_update.from_user.first_name
        members_count = await client.get_chat_members_count(group_id)

        await update_message_count(group_id, 100, 0)
        await client.send_message(group_id, "Default droptime set to 100 messages.")

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

# Custom filter to check if a user is warned
def warned_user_filter(_, __, message: Message):
    user_id = message.from_user.id
    if user_id in warned_users:
        warning_time = warned_users[user_id]
        if time.time() - warning_time < ignore_duration:
            return True  # User is still warned
        else:
            del warned_users[user_id]  # Remove the user from warned list if the warning period has passed
    return False  # User is not warned


async def is_admin_or_special(client: Client, chat_id: int, user_id: int) -> bool:
    if user_id == OWNER_ID or await is_user_sudo(user_id):
        return True
    
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

    if not await is_admin_or_special(client, group_id, user_id):
        await message.reply("You don't have rights to change the droptime in this chat")
        return

    if msg_count < 100 and user_id != OWNER_ID and not await is_user_sudo(user_id):
        await message.reply("Droptime cannot be set to less than 100.")
        return

    await update_message_count(group_id, msg_count, 0)
    await message.reply(f"Random image will be dropped every {msg_count} messages in this group.")



async def check_message_count(client: Client, message: Message):
    user_id = message.from_user.id
    group_id = message.chat.id
    current_time = time.time()

    # Initialize the group in message_timestamps if it doesn't exist
    if group_id not in message_timestamps:
        message_timestamps[group_id] = {}

    # Initialize the user in message_timestamps if they don't exist
    if user_id not in message_timestamps[group_id]:
        message_timestamps[group_id][user_id] = []

    # Add the current timestamp to the user's list
    message_timestamps[group_id][user_id].append(current_time)

    # Keep only the timestamps from the last second
    message_timestamps[group_id][user_id] = [
        ts for ts in message_timestamps[group_id][user_id] if current_time - ts <= 1
    ]

    # Check if the user is already warned and within the ignore period
    if user_id in warned_users and current_time - warned_users[user_id] < ignore_duration:
        return

    # If the user has sent 4 or more messages within 1 second
    if len(message_timestamps[group_id][user_id]) >= 4:
        warned_users[user_id] = current_time  # Update the warning timestamp
        await message.reply(f"{message.from_user.first_name} has been banned from this bot for next 10 minutes !!")
        return

    # Retrieve the current message count for the group
    count_doc = await get_message_count(group_id)

    if count_doc:
        current_count = count_doc["current_count"] + 1
        msg_count = count_doc["msg_count"]

        # If the current count reaches the drop threshold
        if current_count >= msg_count:
            current_count = 0
            character_doc = await get_random_character()
            if not character_doc:
                print("No Characters Available to drop")                 
                return

            character = character_doc[0]
            character_id = character["id"]
            character_url = character["img_url"]
            character_name = character["name"]

            try:
                # Send the photo directly using the URL
                photo_message = await client.send_photo(
                    group_id, 
                    character_url, 
                    caption=f"O-Nee Chan ! New Character Is Here.\nSmash her using /smash name and add her to your collection !!"
                )

                # Construct the message link
                chat_id = photo_message.chat.id
                message_id = photo_message.id
                message_link = f"https://t.me/c/{str(chat_id)[4:]}/{message_id}"

                # Update the drop with the message link
                await update_drop(group_id, character_id, character_name, character_url, message_link)

            except Exception as e:
                print("Failed To Send Image !!")
                

        # Update the current message count for the group
        await update_message_count(group_id, msg_count, current_count)

