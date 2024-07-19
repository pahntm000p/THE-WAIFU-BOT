# BOT/handlers/start.py
from pyrogram import Client, filters

async def start(client, message):
    await message.reply("Hello! I'm a bot created using Pyrogram.")