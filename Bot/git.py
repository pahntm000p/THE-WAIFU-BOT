import os
import sys
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message


async def git_pull_command(client: Client, message: Message):
    try:
        result = subprocess.run(
            ["git", "pull", "https://git-token@github.com/username/reponame.git", "branch-name"],
            capture_output=True, text=True, check=True
        )
        if "Already up to date" in result.stdout:
            return await message.reply("Repo is already up to date")
        elif result.returncode == 0:
            await message.reply(f"Git pull successful. Bot updated.\n\n{result.stdout}")
            await restart_bot(message)
        else:
            await message.reply("Git pull failed. Please check the logs.")
    except subprocess.CalledProcessError as e:
        await message.reply(f"Git pull failed with error: {e.stderr}")

async def restart_bot(message: Message):
    await message.reply("Restarting... 🤯🤯")
    args = [sys.executable, "-m", "Bot"]
    os.execle(sys.executable, *args, os.environ)
    sys.exit()

async def restart_command(client: Client, message: Message):
    try:
        await message.reply("Restarting the bot...")
        os.execvp(sys.executable, [sys.executable, "-m", "Bot"])
    except Exception as e:
        await message.reply(f"Restart failed with error: {str(e)}")
