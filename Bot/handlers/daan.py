from pyrogram import Client, filters
from pyrogram.types import Message
from ..database import get_all_images, update_smashed_image
from ..config import OWNER_ID as BOT_OWNER

async def daan(client: Client, message: Message):
    if message.from_user.id != BOT_OWNER:
        await message.reply("You are not authorized to use this command.")
        return

    if len(message.command) < 2 or not message.reply_to_message:
        await message.reply("Please provide an amount and reply to a user's message.")
        return

    try:
        amount = int(message.command[1])
    except ValueError:
        await message.reply("Please provide a valid number for the amount.")
        return

    user_id = message.reply_to_message.from_user.id
    user = await client.get_users(user_id)

    if user.is_bot:
        await message.reply("You cannot give characters to a bot.")
        return

    # Fetch all available images from the database
    all_images = await get_all_images()

    if not all_images:
        await message.reply("No characters available to give.")
        return

    # Repeat images if the total characters are less than the amount
    images_to_give = (all_images * (amount // len(all_images) + 1))[:amount]

    for image in images_to_give:
        await update_smashed_image(user_id, image["id"], message.reply_to_message.from_user.mention)

    await message.reply(f"Successfully given {amount} characters to {message.reply_to_message.from_user.mention}.")
