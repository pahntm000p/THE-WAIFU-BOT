from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

async def start(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    bot_name = client.me.first_name
    bot_username = client.me.username

    # Create the buttons
    buttons = [
        [InlineKeyboardButton("🍃 Add Me To Your Group", url=f"https://t.me/{bot_username}?startgroup=start")],
        [InlineKeyboardButton("Support", url="https://t.me/dominosXD"), InlineKeyboardButton("Updates", url="https://t.me/Smash_Waifu_Support")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    # Define the image URL and caption
    image_url = "https://graph.org//file/2d839f92769ef6778e0e6.jpg"
    caption = (
        f"**Greetings {first_name} , I am {bot_name} !!**\n\n"
        "✵ **Here’s What I Offer:**\n"
        "• **✨ Random Waifus:** I introduce a variety of random waifus into your group.\n"
        "• **🔍 Smash & Collect:** Engage with the characters by smashing them and adding them to your exclusive collection.\n"
        "• **📂 Public Collections:** Showcase your curated collections for all to see and admire.\n"
        "• **🌟 Enriched Group Dynamics:** I enhance your group’s interaction with a unique and immersive experience.\n\n"
        "📝 **To explore my full range of commands and functionalities, simply use** /help."
    )

    # Send the image with caption
    await client.send_photo(
        chat_id=message.chat.id,
        photo=image_url,
        caption=caption,
        reply_markup=reply_markup
    )
