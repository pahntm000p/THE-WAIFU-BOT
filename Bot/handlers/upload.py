# BOT/handlers/upload.py
from pyrogram import Client, filters
from pyrogram.types import Message
from Bot.database import db, get_next_id
from datetime import datetime, timedelta

# Mapping for rarity
RARITY_MAPPING = {
    "1": {"name": "Common", "sign": "⚪️"},
    "2": {"name": "Rare", "sign": "🟠"},
    "3": {"name": "Legendary", "sign": "🟡"},
    "4": {"name": "Medium", "sign": "🟢"},
    "5": {"name": "Limited Time", "sign": "🔴"}  # Add this line
}


async def upload(client: Client, message: Message):
    try:
        # Extract parameters from the command
        params = message.text.split()
        if len(params) < 5 or len(params) > 6:
            await message.reply("Usage: /upload {img_url} {name} {anime} {rarity} [days]")
            return

        _, img_url, name, anime, rarity, *days = params

        # Replace hyphens with spaces in name and anime
        name = name.replace("-", " ")
        anime = anime.replace("-", " ")

        # Validate rarity
        if rarity not in RARITY_MAPPING:
            await message.reply("Invalid rarity. Please use 1, 2, 3, 4, or 5.")
            return

        rarity_info = RARITY_MAPPING[rarity]

        # Generate a new unique ID for the character
        new_id = await get_next_id()

        # Set the expiry time if provided
        expiry = None
        if rarity == "5":  # Limited Time
            if not days:
                await message.reply("Please provide the number of days for Limited Time rarity.")
                return
            try:
                # Parse the number of days
                num_days = int(days[0])
                expiry = datetime.utcnow() + timedelta(days=num_days)
            except ValueError:
                await message.reply("Invalid number of days. Please provide a valid integer.")
                return

        # Create the new character document
        character = {
            "id": f"{new_id:02}",
            "img_url": img_url,
            "name": name,
            "anime": anime,
            "rarity": rarity_info["name"],
            "rarity_sign": rarity_info["sign"],
            "expiry_time": expiry
        }

        # Insert the character into the database
        await db.Characters.insert_one(character)
        expiry_message = f" for {num_days} days" if expiry else ""
        await message.reply(f"Character {name} added successfully with ID {new_id:02} as {rarity_info['name']} {rarity_info['sign']}{expiry_message}.")

    except Exception as e:
        await message.reply(f"An error occurred: {e}")


async def edit_character(client: Client, message: Message):
    try:
        # Extract parameters from the command
        params = message.text.split(maxsplit=2)
        if len(params) < 3:
            await message.reply("Usage: /edit {id} field=value [field=value ...]")
            return

        char_id = params[1]
        updates = {}

        # Parse the update fields
        for param in params[2].split():
            if '=' not in param:
                await message.reply(f"Invalid parameter: {param}. Use field=value format.")
                return
            field, value = param.split('=', 1)
            if field == "img_url":
                updates["img_url"] = value
            elif field == "name":
                updates["name"] = value.replace("-", " ")
            elif field == "anime":
                updates["anime"] = value.replace("-", " ")
            elif field == "rarity":
                if value not in RARITY_MAPPING:
                    await message.reply("Invalid rarity. Please use 1, 2, 3, or 4.")
                    return
                rarity_info = RARITY_MAPPING[value]
                updates["rarity"] = rarity_info["name"]
                updates["rarity_sign"] = rarity_info["sign"]
            else:
                await message.reply(f"Invalid field: {field}. Allowed fields are img_url, name, anime, rarity.")
                return

        # Check if there are any updates to apply
        if not updates:
            await message.reply("No valid fields to update.")
            return

        # Find the character by ID
        character = await db.Characters.find_one({"id": char_id})
        if not character:
            await message.reply(f"No character found with ID {char_id}.")
            return

        # Update the character details
        await db.Characters.update_one({"id": char_id}, {"$set": updates})
        await message.reply(f"Character with ID {char_id} updated successfully.")

    except Exception as e:
        await message.reply(f"An error occurred: {e}")
