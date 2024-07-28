from pyrogram import Client, filters
from pyrogram.types import Message
from ..database import db, get_random_character, update_smashed_image
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from ..config import OWNER_ID
from pyrogram.enums import ChatMemberStatus
import os 

BOT_OWNER = OWNER_ID
CLAIM_INTERVAL = timedelta(hours=24)

async def is_subscribed(client: Client, user_id: int, group_id: int) -> bool:
    try:
        member = await client.get_chat_member(group_id, user_id)
        return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception as e:
        print(f"Error checking subscription status: {e}")
        return False

async def get_chat_username(client: Client, chat_id: int) -> str:
    try:
        chat = await client.get_chat(chat_id)
        return chat.username
    except Exception as e:
        print(f"Error fetching chat username: {e}")
        return None

async def claim(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = await db.Users.find_one({"user_id": user_id})
    
    # Check if force-subscription is enabled
    force_sub = await db.Settings.find_one({"setting": "force_sub"})
    if force_sub and force_sub.get("enabled"):
        group_ids = force_sub.get("group_ids", [])
        buttons = []
        for group_id in group_ids:
            if not await is_subscribed(client, user_id, group_id):
                chat_username = await get_chat_username(client, group_id)
                if chat_username:
                    buttons.append(InlineKeyboardButton(text="Join Group", url=f"https://t.me/{chat_username}"))
        
        if buttons:
            keyboard = InlineKeyboardMarkup([buttons])
            await message.reply("**Please join our groups and try again !**", reply_markup=keyboard)
            return
    
    if user_data:
        last_claim_time = user_data.get("last_claim_time")
        if last_claim_time and datetime.utcnow() - last_claim_time < CLAIM_INTERVAL:
            time_remaining = last_claim_time + CLAIM_INTERVAL - datetime.utcnow()
            hours, remainder = divmod(time_remaining.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            await message.reply(f"⏳ **You can claim your next character in {int(hours)}h {int(minutes)}m.**")
            return

    # Fetch a random character
    random_character = await get_random_character()
    if not random_character:
        await message.reply("🚫 No characters available for claiming at the moment. Please try again later.")
        return

    random_character = random_character[0]

    # Update user's collection
    await update_smashed_image(user_id, random_character["id"], message.from_user.first_name)
    await db.Users.update_one(
        {"user_id": user_id},
        {"$set": {"last_claim_time": datetime.utcnow()}},
        upsert=True
    )
    
    # Prepare and send the message with the character's image and caption
    img_url = random_character["img_url"]
    user_mention = message.from_user.mention
    caption = (
        f"**🫧 {user_mention} you got a new character!**\n\n"
        f"✨ **Name**: {random_character['name']}\n"
        f"{random_character['rarity_sign']} **Rarity**: {random_character['rarity']}\n"
        f"🍁 **Anime**: {random_character['anime']}\n\n"
        f"🆔: {random_character['id']}"
    )
    
    await client.send_photo(
        chat_id=message.chat.id,
        photo=img_url,
        caption=caption
    )


# Register the command handler
async def claim_handler(client, message: Message):
    await claim(client, message)

async def set_force_sub(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        await message.reply("🚫 You don't have the rights to perform this action.")
        return
    
    if len(message.command) < 2:
        await message.reply("⚠️ Please specify 'enable' or 'disable'.")
        return
    
    action = message.command[1].lower()
    if action not in ["enable", "disable"]:
        await message.reply("⚠️ Invalid action. Please specify 'enable' or 'disable'.")
        return
    
    enabled = action == "enable"
    await db.Settings.update_one(
        {"setting": "force_sub"},
        {"$set": {"enabled": enabled}},
        upsert=True
    )
    await message.reply(f"✅ Force-subscription has been {'enabled' if enabled else 'disabled'}.")


# Command to add or remove group links for force-subscription
async def manage_group_ids(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        await message.reply("🚫 You don't have the rights to perform this action.")
        return
    
    if len(message.command) < 3:
        await message.reply("⚠️ Please specify 'add' or 'remove' followed by the group IDs.")
        return
    
    action = message.command[1].lower()
    group_ids = [int(id) for id in message.command[2:]]

    if action not in ["add", "remove"]:
        await message.reply("⚠️ Invalid action. Please specify 'add' or 'remove'.")
        return
    
    force_sub = await db.Settings.find_one({"setting": "force_sub"})
    current_ids = force_sub.get("group_ids", []) if force_sub else []

    if action == "add":
        current_ids.extend(group_ids)
    elif action == "remove":
        current_ids = [id for id in current_ids if id not in group_ids]

    await db.Settings.update_one(
        {"setting": "force_sub"},
        {"$set": {"group_ids": current_ids}},
        upsert=True
    )
    await message.reply(f"✅ Group IDs have been successfully {'added' if action == 'add' else 'removed'}.")



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


async def send_logs(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        await message.reply_text("🚫 This command is restricted to the bot owner.")
        return

    log_file_path = "bot.log"
    
    if not os.path.exists(log_file_path):
        await message.reply_text("No log file found.")
        return

    await message.reply_document(log_file_path)

def add_logs_handler(app: Client):
    @app.on_message(filters.command("logs"))
    async def handle_logs(client: Client, message: Message):
        await send_logs(client, message)


async def transfer_collection(client: Client, message: Message):
    if message.from_user.id != BOT_OWNER:
        await message.reply("You are not authorized to use this command.")
        return

    try:
        from_user_id, to_user_id = map(int, message.command[1:])
    except (ValueError, IndexError):
        await message.reply("**Usage: /transfer from_user_id to_user_id**")
        return

    from_collection = await db.Collection.find_one({"user_id": from_user_id})
    to_collection = await db.Collection.find_one({"user_id": to_user_id})

    if not from_collection:
        await message.reply("The source user does not have any collection.")
        return

    if not to_collection:
        to_collection = {"user_id": to_user_id, "images": []}

    # Merge the collections
    to_images = {img["image_id"]: img for img in to_collection["images"]}
    for img in from_collection["images"]:
        if img["image_id"] in to_images:
            to_images[img["image_id"]]["count"] += img["count"]
        else:
            to_images[img["image_id"]] = img

    to_collection["images"] = list(to_images.values())

    # Update the target user's collection in the database
    await db.Collection.update_one(
        {"user_id": to_user_id},
        {"$set": to_collection},
        upsert=True
    )

    # Remove the source user's collection from the database
    await db.Collection.delete_one({"user_id": from_user_id})

    await message.reply("**Collection successfully transferred.**")
