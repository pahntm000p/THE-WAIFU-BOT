from pyrogram import Client, filters
from pyrogram.types import Message
from ..database import ban_user, unban_user, is_user_banned, add_sudo_user, remove_sudo_user, is_user_sudo
from ..config import OWNER_ID as BOT_OWNER
from ..database import db
async def ban(client: Client, message: Message):
    if message.from_user.id != BOT_OWNER and not await is_user_sudo(message.from_user.id):
        await message.reply("**You are not authorized to use this command.**")
        return

    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply("**Please provide a user ID or reply to a user's message.**")
        return

    user_id = int(message.command[1]) if len(message.command) > 1 else message.reply_to_message.from_user.id
    user = await client.get_users(user_id)
    first_name = user.first_name

    if await is_user_banned(user_id):
        await message.reply(f"**{first_name} is already banned from this bot.**")
        return

    await ban_user(user_id)
    await message.reply(f"**{first_name} has been permanently banned from this bot.**")

async def unban(client: Client, message: Message):
    if message.from_user.id != BOT_OWNER and not await is_user_sudo(message.from_user.id):
        await message.reply("**You are not authorized to use this command.**")
        return

    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply("**Please provide a user ID or reply to a user's message.**")
        return

    user_id = int(message.command[1]) if len(message.command) > 1 else message.reply_to_message.from_user.id
    user = await client.get_users(user_id)
    first_name = user.first_name

    if not await is_user_banned(user_id):
        await message.reply(f"**{first_name} is already free to use this bot.**")
        return

    await unban_user(user_id)
    await message.reply(f"**{first_name} has been unbanned from this bot.**")

async def add_sudo(client: Client, message: Message):
    if message.from_user.id != BOT_OWNER:
        await message.reply("**You are not authorized to use this command.**")
        return

    if len(message.command) < 2:
        await message.reply("**Please provide a user ID.**")
        return

    user_id = int(message.command[1])
    user = await client.get_users(user_id)
    first_name = user.first_name

    if await is_user_sudo(user_id):
        await message.reply(f"**{first_name} already has sudo powers.**")
        return

    await add_sudo_user(user_id)
    await message.reply(f"**{first_name} has been added as a sudo user.**")

async def remove_sudo(client: Client, message: Message):
    if message.from_user.id != BOT_OWNER:
        await message.reply("**You are not authorized to use this command.**")
        return

    if len(message.command) < 2:
        await message.reply("**Please provide a user ID.**")
        return

    user_id = int(message.command[1])
    user = await client.get_users(user_id)
    first_name = user.first_name

    if not await is_user_sudo(user_id):
        await message.reply(f"**{first_name} is already a normal user.**")
        return

    await remove_sudo_user(user_id)
    await message.reply(f"**{first_name} has been removed as a sudo user.**")


async def sudoers(client: Client, message: Message):
    if message.from_user.id != BOT_OWNER:
        await message.reply("You are not authorized to use this command.")
        return

    sudo_users = await db.Sudo.find().to_list(length=None)
    if not sudo_users:
        await message.reply("There are no sudo users.")
        return

    sudo_list = []
    for i, sudo in enumerate(sudo_users, 1):
        user = await client.get_users(sudo['user_id'])
        user_mention = user.mention if user else f"User ID {sudo['user_id']}"
        sudo_list.append(f"{i}. {user_mention} -> {sudo['user_id']}")

    sudo_message = "\n".join(sudo_list)
    await message.reply(f"List of sudo users:\n\n{sudo_message}")
