# BOT/handlers/leaderboard.py
from pyrogram import Client, filters
from pyrogram.types import Message
from Bot.database import db

async def fetch_user_names(client, user_ids):
    users = await client.get_users(user_ids)
    return {user.id: user.mention for user in users}

async def generate_leaderboard_text(title, leaderboard, emoji):
    text = f"{emoji}** {title} **{emoji}\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for index, entry in enumerate(leaderboard, start=1):
        rank = medals[index - 1] if index <= 3 else f"**{index}**"
        text += f"{rank} {entry['mention']} —> **{entry['total_characters']} ({entry['total_unique_characters']})**\n"
    return text

async def top(client: Client, message: Message):
    fetching_msg = await message.reply("Fetching leaderboard details...")

    # Fetch all member IDs in the group chat
    member_ids = [member.user.id async for member in client.get_chat_members(message.chat.id)]

    # Fetch collection details for each member
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

    # Sort the leaderboard by total characters
    leaderboard.sort(key=lambda x: x["total_characters"], reverse=True)

    # Fetch the user names
    user_ids = [entry["user_id"] for entry in leaderboard[:10]]
    user_mentions = await fetch_user_names(client, user_ids)

    # Update leaderboard with user mentions
    for entry in leaderboard[:10]:
        entry["mention"] = user_mentions[entry["user_id"]]

    # Generate the leaderboard text
    group_name = message.chat.title if message.chat.title else "Group"
    leaderboard_text = await generate_leaderboard_text(f"{group_name}'s Top 10 Smashers", leaderboard[:10], "⛩")

    await fetching_msg.delete()
    await message.reply(leaderboard_text)

async def stop(client: Client, message: Message):
    fetching_msg = await message.reply("Fetching global leaderboard details...")

    # Fetch collection details for all users
    collections = await db.Collection.find({}).to_list(length=None)

    # Generate the leaderboard
    leaderboard = []
    for user_collection in collections:
        total_characters = sum(image["count"] for image in user_collection["images"])
        total_unique_characters = len(user_collection["images"])
        leaderboard.append({
            "user_id": user_collection["user_id"],
            "total_characters": total_characters,
            "total_unique_characters": total_unique_characters
        })

    # Sort the leaderboard by total characters
    leaderboard.sort(key=lambda x: x["total_characters"], reverse=True)

    # Fetch the user names
    user_ids = [entry["user_id"] for entry in leaderboard[:10]]
    user_mentions = await fetch_user_names(client, user_ids)

    # Update leaderboard with user mentions
    for entry in leaderboard[:10]:
        entry["mention"] = user_mentions[entry["user_id"]]

    # Generate the leaderboard text
    leaderboard_text = await generate_leaderboard_text("Global Top 10 Smashers", leaderboard[:10], "🌎")

    await fetching_msg.delete()
    await message.reply(leaderboard_text)
