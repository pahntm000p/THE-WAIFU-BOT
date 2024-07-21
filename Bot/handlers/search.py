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

async def send_inline_query_button(client, message):
    user_id = message.from_user.id
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Search Smashed Waifus", switch_inline_query_current_chat=f"smashed.{user_id}")]
        ]
    )
    await message.reply("Hello", reply_markup=keyboard)