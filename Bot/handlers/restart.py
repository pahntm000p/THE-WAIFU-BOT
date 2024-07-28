import subprocess
import os
from pyrogram import Client, filters
from pyrogram.types import Message
from ..config import OWNER_ID as BOT_OWNER


# Command to handle /restart
async def restart_bot(client: Client, message: Message):
    if message.from_user.id == BOT_OWNER:  # Ensure only the bot owner can run this command
        await message.reply_text("Bot is going to restart...")
        # Notify owner about the restart
        await client.send_message(chat_id=BOT_OWNER, text="Bot is restarting...")

        # Restart the bot
        os.system("python3 -m Bot &")
        await client.send_message(chat_id=BOT_OWNER, text="Bot has restarted.")
        # Stop the current instance
        os._exit(0)
    else:
        await message.reply_text("You are not authorized to run this command.")
