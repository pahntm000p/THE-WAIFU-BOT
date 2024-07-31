from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

async def help(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    bot_name = client.me.first_name
    bot_username = client.me.username

    # Create the buttons
    buttons = [
        [InlineKeyboardButton("Support", url="https://t.me/dominosXD"), 
         InlineKeyboardButton("Updates", url="https://t.me/Smash_Waifu_Support")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    # Define the image URL and caption
    image_url = "https://graph.org//file/2d839f92769ef6778e0e6.jpg"
    caption = (
    f"**⥼ Command Overview ⥽**\n\n"
    f"🔹 **/smash** - Capture and add a waifu to your collection.\n"
    f"🔹 **/smashes** - Showcase your collection of waifus.\n"
    f"🔹 **/gtop** - Access the global leaderboard for top collectors.\n"
    f"🔹 **/tdtop** - View today's top smashers.\n"
    f"🔹 **/ctop** - See which chat has the most smashes.\n"
    f"🔹 **/top** - Display the top smashers within your group.\n"
    f"🔹 **/droptime** - Adjust the timing for waifu drops in your groups.\n"
    f"🔹 **/gtrade** - Propose a global trade for a character.\n"
    f"🔹 **/gtreq** - Toggle global trade request notifications.\n"
    f"🔹 **/smode** - Customize how your collection is displayed.\n"
    f"🔹 **/cmode** - Set your preferred caption style.\n"
    f"🔹 **/fav** - Mark a character as your favorite.\n"
    f"🔹 **/sstatus** - Review your current status and achievements.\n"
    f"🔹 **/claim** - Claim a free waifu daily.\n"
    f"🔹 **/upreq** - Request the addition of a new character.\n"
    f"🔹 **/sanime** - Search through all available anime in the bot.\n"
)


    # Send the image with caption
    await client.send_photo(
        chat_id=message.chat.id,
        photo=image_url,
        caption=caption,
        reply_markup=reply_markup
    )
