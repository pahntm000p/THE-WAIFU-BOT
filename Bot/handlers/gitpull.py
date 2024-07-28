import subprocess
import os
from pyrogram import Client, filters
from pyrogram.types import Message
from ..config import OWNER_ID as BOT_OWNER

async def git_pull(client: Client, message: Message):
    if message.from_user.id == BOT_OWNER:  # Ensure only the bot owner can run this command
        try:
            # Path to the batch script
            script_path = os.path.join(os.getcwd(), "git_pull.bat")
            
            # Execute the batch script
            result = subprocess.run([script_path], capture_output=True, text=True, shell=True)
            
            if result.returncode == 0:
                await message.reply_text(f"Successfully pulled updates:\n\n{result.stdout}")
            else:
                await message.reply_text(f"Error pulling updates:\n\n{result.stderr}")
        except Exception as e:
            await message.reply_text(f"Exception occurred:\n\n{str(e)}")
    else:
        await message.reply_text("You are not authorized to run this command.")

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
