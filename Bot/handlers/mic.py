from pyrogram import Client
from pyrogram.types import Message
from ..database import db

async def get_character_details(image_id):
    return await db.Characters.find_one({"id": image_id})

async def get_global_smash_count(image_id):
    collections = await db.Collection.find({"images.image_id": image_id}).to_list(length=None)
    unique_user_ids = set()
    total_smash_count = 0
    for collection in collections:
        for image in collection["images"]:
            if image["image_id"] == image_id:
                total_smash_count += image["count"]
                unique_user_ids.add(collection["user_id"])
    unique_user_count = len(unique_user_ids)
    return total_smash_count, unique_user_count

async def check_character(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Please provide the character ID to check.")
        return

    character_id = message.command[1]

    # Fetch character details
    character = await get_character_details(character_id)
    if not character:
        await message.reply("Character details not found.")
        return

    # Fetch global smash count and unique user count
    global_smash_count, unique_user_count = await get_global_smash_count(character_id)

    # Create the caption
    caption = (
        f"✨**Name** **:** **{character['name']}**\n"
        f"{character['rarity_sign']} **Rarity** **:** **{character['rarity']}**\n"
        f"🍁**Anime** **:** **{character['anime']}**\n\n"
        f"🆔 **:** **{character['id']}**\n\n"
        f"☘️**Globally Smashed {unique_user_count} Times**"
    )

    # Send the photo with the caption
    await client.send_photo(
        chat_id=message.chat.id,
        photo=character["img_url"],
        caption=caption
    )
