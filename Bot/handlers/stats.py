from pyrogram import Client
from pyrogram.types import Message
from ..database import db

async def handle_stats(client: Client, message: Message):
    # Get the count of all group IDs
    group_count = await db.MessageCounts.count_documents({})
    
    # Get the total number of users
    user_count = await db.TotalUsers.count_documents({})
    
    # Format the stats message
    stats_message = (
        f"📊 **Bot Stats** 📊\n\n"
        f"👥 **Total Groups:** `{group_count}`\n"
        f"👤 **Total Users:** `{user_count}`\n"
    )
    
    # Send the stats message to the owner
    await message.reply_text(stats_message)
