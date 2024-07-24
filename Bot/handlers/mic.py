from pyrogram import Client, filters
from pyrogram.types import Message
from ..database import db
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton



async def get_character_details(image_id):
    return await db.Characters.find_one({"id": image_id})

async def get_total_uploaded_characters():
    return await db.Characters.count_documents({})


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

async def fetch_user_names(client, user_ids):
    users = await client.get_users(user_ids)
    return {user.id: user.mention for user in users}

async def get_leaderboard_data():
    collections = await db.Collection.find({}).to_list(length=None)
    leaderboard = []
    for user_collection in collections:
        total_characters = sum(image["count"] for image in user_collection["images"])
        total_unique_characters = len(user_collection["images"])
        leaderboard.append({
            "user_id": user_collection["user_id"],
            "total_characters": total_characters,
            "total_unique_characters": total_unique_characters
        })
    leaderboard.sort(key=lambda x: x["total_characters"], reverse=True)
    return leaderboard

async def get_chat_leaderboard_data(client, chat_id):
    member_ids = []
    async for member in client.get_chat_members(chat_id):
        member_ids.append(member.user.id)
    leaderboard = []
    for user_id in member_ids:
        user_collection = await db.Collection.find_one({"user_id": user_id})
        if user_collection and user_collection.get("images"):
            total_characters = sum(image["count"] for image in user_collection["images"])
            total_unique_characters = len(user_collection["images"])
            leaderboard.append({
                "user_id": user_id,
                "total_characters": total_characters,
                "total_unique_characters": total_unique_characters
            })
    leaderboard.sort(key=lambda x: x["total_characters"], reverse=True)
    return leaderboard


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
        f"✨**Name**: **{character['name']}**\n"
        f"{character['rarity_sign']} **Rarity**: **{character['rarity']}**\n"
        f"🍁**Anime**: **{character['anime']}**\n\n"
        f"🆔 **ID**: **{character['id']}**\n\n"
        f"☘️ **Globally Smashed**: {unique_user_count} Times"
    )

    # Create inline keyboard with the "Smashers" button
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Show Smashers", callback_data=f"show_smashers_{character_id}")]]
    )

    # Send the photo with the caption and the button
    await client.send_photo(
        chat_id=message.chat.id,
        photo=character["img_url"],
        caption=caption,
        reply_markup=keyboard
    )

async def show_smashers(client: Client, callback_query):
    character_id = callback_query.data.split('_')[2]
    chat_id = callback_query.message.chat.id

    # Fetch user collections in the chat
    member_ids = [member.user.id async for member in client.get_chat_members(chat_id)]
    smashers = []
    for user_id in member_ids:
        user_collection = await db.Collection.find_one({"user_id": user_id})
        if user_collection:
            for image in user_collection.get("images", []):
                if image["image_id"] == character_id:
                    smashers.append({"user_id": user_id, "count": image["count"]})

    # Fetch user names
    user_mentions = await fetch_user_names(client, [smasher["user_id"] for smasher in smashers])
    smasher_text = "\n".join([f"{user_mentions[smasher['user_id']]} --> {smasher['count']}" for smasher in smashers])

    # Edit the message with smashers details
    await callback_query.edit_message_text(
        callback_query.message.caption + "\n\n----------Smashers----------\n" + smasher_text,
        parse_mode=ParseMode.HTML
    )

async def sstatus(client: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    # Fetch user collection
    user_collection = await db.Collection.find_one({"user_id": user_id})
    if not user_collection:
        await message.reply("No collection found for this user.")
        return
    
    total_uploaded_characters = await get_total_uploaded_characters()

    # Calculate total waifus and harem count
    total_waifus = sum(image["count"] for image in user_collection.get("images", []))
    unique_waifus = len(user_collection.get("images", []))
    harem_percentage = (unique_waifus / total_uploaded_characters) * 100 if total_uploaded_characters > 0 else 0

    # Get rarities count
    rarities = {"Legendary": 0, "Rare": 0, "Medium": 0, "Common": 0}
    for image in user_collection.get("images", []):
        character = await get_character_details(image["image_id"])
        if character and character["rarity"] in rarities:
            rarities[character["rarity"]] += 1

    # Fetch global leaderboard data
    global_leaderboard = await get_leaderboard_data()

    if message.chat.type != "private":
        try:
            chat_leaderboard = await get_chat_leaderboard_data(client, message.chat.id)
            chat_position = next((index + 1 for index, entry in enumerate(chat_leaderboard) if entry["user_id"] == user_id), len(chat_leaderboard))
        except Exception as e:
            chat_position = 1
    else:
        chat_position = 1

    # Calculate user positions
    global_position = next((index + 1 for index, entry in enumerate(global_leaderboard) if entry["user_id"] == user_id), len(global_leaderboard))

    # Fetch one character's image
    if user_collection.get("images"):
        character = await get_character_details(user_collection["images"][0]["image_id"])
        character_img_url = character["img_url"]
    else:
        character_img_url = None

        # Create the status message
    status_message = (
        "-----🌸 Grabber Status 🌸-----\n\n"
        f"---> 👤 User : {user_name}\n"
        f"---> 🐙 User ID : {user_id}\n"
        f"---> ✨ Total Smashes : {total_waifus} ({unique_waifus})\n"
        f"---> 🍁 Collection : {unique_waifus}/{total_uploaded_characters} ({harem_percentage:.2f}%)\n\n"
        "----------------------------------\n\n"
        f"---> 🟡 Rarity: Legendary -- {rarities['Legendary']}\n"
        f"---> 🟠 Rarity: Rare -- {rarities['Rare']}\n"
        f"---> 🔴 Rarity: Medium -- {rarities['Medium']}\n"
        f"---> 🔵 Rarity: Common -- {rarities['Common']}\n\n"
        "----------------------------------\n"
        f"---> 🌍 Position Globally : {global_position}\n"
        f"---> 💬 Chat Position : {chat_position:02d}\n"
    )
    
    # Send the status message with character image as caption
    if character_img_url:
        await client.send_photo(
            chat_id=message.chat.id,
            photo=character_img_url,
            caption=status_message,
            parse_mode=ParseMode.HTML
        )
    else:
        await message.reply(status_message)


