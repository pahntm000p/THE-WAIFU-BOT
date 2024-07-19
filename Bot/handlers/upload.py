# BOT/handlers/upload.py
from pyrogram import Client, filters
from pyrogram.types import Message
from Bot.database import db, get_next_id

# Mapping for rarity
RARITY_MAPPING = {
    "1": {"name": "Common", "sign": "⚪️"},
    "2": {"name": "Rare", "sign": "🟣"},
    "3": {"name": "Legendary", "sign": "🟡"},
    "4": {"name": "Medium", "sign": "🟢"},
}

async def upload(client: Client, message: Message):
    try:
        # Extract parameters from the command
        params = message.text.split()
        if len(params) != 5:
            await message.reply("Usage: /upload {img_url} {name} {anime} {rarity}")
            return

        _, img_url, name, anime, rarity = params

        # Replace hyphens with spaces in name and anime
        name = name.replace("-", " ")
        anime = anime.replace("-", " ")

        # Validate rarity
        if rarity not in RARITY_MAPPING:
            await message.reply("Invalid rarity. Please use 1, 2, 3, or 4.")
            return

        rarity_info = RARITY_MAPPING[rarity]

        # Generate a new unique ID for the character
        new_id = await get_next_id()

        # Create the new character document
        character = {
            "id": f"{new_id:02}",
            "img_url": img_url,
            "name": name,
            "anime": anime,
            "rarity": rarity_info["name"],
            "rarity_sign": rarity_info["sign"]
        }

        # Insert the character into the database
        await db.Characters.insert_one(character)
        await message.reply(f"Character {name} added successfully with ID {new_id:02} as {rarity_info['name']} {rarity_info['sign']}.")

    except Exception as e:
        await message.reply(f"An error occurred: {e}")
