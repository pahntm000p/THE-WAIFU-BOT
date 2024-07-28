# BOT/handlers/search.py
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def search(client, message):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Search Waifus", switch_inline_query_current_chat="")]
        ]
    )
    await message.reply("☘️ **Search all the waifus uploaded by clicking the button below**", reply_markup=keyboard)

