from pyrogram import Client, filters
from pyrogram.types import Message
from Bot.database import db
from Bot.config import OWNER_ID as BOT_OWNER

async def broadcast_message(client: Client, message: Message):
    if message.from_user.id != BOT_OWNER:
        await message.reply("**You are not authorized to use this command.**")
        return

    if not message.reply_to_message:
        await message.reply("**Reply to a message to broadcast it.**")
        return

    # Get the message to be broadcasted
    broadcast_msg = message.reply_to_message

    # Fetch all user IDs from the TotalUsers collection
    user_ids = [doc["user_id"] async for doc in db.TotalUsers.find({})]

    # Fetch all group IDs from the MessageCounts collection
    group_ids = [doc["group_id"] async for doc in db.MessageCounts.find({})]

    # Track the count of successful broadcasts
    user_count = 0
    group_count = 0

    # Send the broadcast message to each user
    for user_id in user_ids:
        try:
            await broadcast_msg.forward(chat_id=user_id)
            user_count += 1
        except Exception as e:
            print(f"Failed to send message to user {user_id}: {e}")

    # Send the broadcast message to each group
    for group_id in group_ids:
        try:
            await broadcast_msg.forward(chat_id=group_id)
            group_count += 1
        except Exception as e:
            print(f"Failed to send message to group {group_id}: {e}")

    await message.reply(f"**Broadcast completed.**\n\n**Users reached:** {user_count}\n**Groups reached:** {group_count}")

async def handle_broadcast(client: Client, message: Message):
    await broadcast_message(client, message)
