import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from ..database import db
from .. import app
from pyrogram.enums import ChatType

# Store temporary data for guild creation, joining, and management processes
guild_creation_data = {}
guild_join_data = {}
guild_management_data = {}

# Function to generate a unique 10-digit guild ID
async def get_unique_guild_id():
    while True:
        guild_id = ''.join(random.choices("0123456789", k=10))
        existing_guild = await db.Guilds.find_one({"guild_id": guild_id})
        if not existing_guild:
            return guild_id

# Function to calculate total waifus owned by guild members
async def calculate_total_waifus(guild_members):
    total_waifus = 0
    for user_id in guild_members:
        user_collection = await db.Collection.find_one({"user_id": user_id})
        if user_collection and "images" in user_collection:
            total_waifus += sum(image["count"] for image in user_collection["images"])
    return total_waifus

@app.on_message(filters.command("guild"))
async def guild_command(client: Client, message: Message):
    user_id = message.from_user.id
    user_guild = await db.Guilds.find_one({"members": user_id})

    if user_guild:
        is_owner = user_guild['owner_id'] == user_id
        guild_info = f"""
✨ **Guild Name:** `{user_guild['guild_name']}`
🏅 **Guild ID:** `{user_guild['guild_id']}`
👥 **Total Members:** `{len(user_guild['members'])}`
🎴 **Total Waifus Owned by Members:** `{await calculate_total_waifus(user_guild['members'])}`
        """

        if message.chat.type == ChatType.PRIVATE:
            if is_owner:
                keyboard = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("🔄 Transfer Ownership", callback_data="confirm_transfer_ownership")],
                        [InlineKeyboardButton("🗑️ Delete Guild", callback_data="confirm_delete_guild")]
                    ]
                )
                await message.reply_text(f"🔱 **Guild Management:**\n\n{guild_info}\n\n⚙️ **Choose an action:**", reply_markup=keyboard)
            else:
                keyboard = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("🚪 Leave Guild", callback_data="confirm_leave_guild")]
                    ]
                )
                await message.reply_text(f"🔱 **You are a member of:**\n\n{guild_info}", reply_markup=keyboard)
        elif message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await message.reply_text(f"🔱 **Guild Info:**\n\n{guild_info}")

    else:
        if message.chat.type == ChatType.PRIVATE:
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🛡️ Create Guild", callback_data="create_guild")],
                    [InlineKeyboardButton("⚔️ Join Guild", callback_data="join_guild")]
                ]
            )
            await message.reply_text("⚙️ **Choose an option:**", reply_markup=keyboard)
        elif message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await message.reply_text("❌ **You are not a member of any guild.**\nPlease use this command in private chat to create or join a guild.")

@app.on_callback_query(filters.regex(r"confirm_transfer_ownership"))
async def confirm_transfer_ownership(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_guild = await db.Guilds.find_one({"owner_id": user_id})
    if user_guild:
        guild_management_data[user_id] = "transfer_ownership"
        await callback_query.message.delete()
        await callback_query.message.reply_text("🔄 **Please enter the user ID of the member you want to transfer ownership to:**")
    else:
        await callback_query.message.reply_text("❌ **You do not own any guild to transfer ownership.**", quote=True)

@app.on_callback_query(filters.regex(r"confirm_delete_guild"))
async def confirm_delete_guild(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("❌ No, Cancel", callback_data="cancel_action")],
            [InlineKeyboardButton("🗑️ Yes, Delete", callback_data="delete_guild")]
        ]
    )
    await callback_query.message.reply_text("⚠️ **Are you sure you want to delete the guild?** This action cannot be undone.", reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"confirm_leave_guild"))
async def confirm_leave_guild(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("❌ No, Cancel", callback_data="cancel_action")],
            [InlineKeyboardButton("🚪 Yes, Leave", callback_data="leave_guild")]
        ]
    )
    await callback_query.message.reply_text("⚠️ **Are you sure you want to leave the guild?**", reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"cancel_action"))
async def cancel_action(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    await callback_query.message.reply_text("❌ **Action canceled.**", quote=True)

@app.on_callback_query(filters.regex(r"delete_guild"))
async def delete_guild(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_guild = await db.Guilds.find_one({"owner_id": user_id})

    if user_guild:
        await db.Guilds.delete_one({"guild_id": user_guild["guild_id"]})
        await callback_query.message.delete()
        await callback_query.message.reply_text("🗑️ **Guild has been deleted successfully.**")
    else:
        await callback_query.message.reply_text("❌ **You do not own any guild.**", quote=True)

@app.on_callback_query(filters.regex(r"leave_guild"))
async def leave_guild(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_guild = await db.Guilds.find_one({"members": user_id})

    if user_guild:
        if user_guild['owner_id'] == user_id:
            await callback_query.message.reply_text("❌ **You are the owner of the guild. Transfer ownership before leaving.**", quote=True)
        else:
            await db.Guilds.update_one({"guild_id": user_guild["guild_id"]}, {"$pull": {"members": user_id}})
            await callback_query.message.delete()
            await callback_query.message.reply_text("🚪 **You have successfully left the guild.**")
    else:
        await callback_query.message.reply_text("❌ **You are not part of any guild.**", quote=True)

@app.on_callback_query(filters.regex(r"transfer_ownership"))
async def transfer_ownership(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_guild = await db.Guilds.find_one({"owner_id": user_id})

    if user_guild:
        guild_management_data[user_id] = "transfer_ownership"
        await callback_query.message.edit_text("🔄 **Please enter the user ID of the member you want to transfer ownership to:**")
    else:
        await callback_query.message.reply_text("❌ **You are not the owner of any guild.**")

@app.on_callback_query(filters.regex(r"create_guild"))
async def create_guild(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    existing_guild = await db.Guilds.find_one({"members": user_id})

    if existing_guild:
        await callback_query.message.reply_text("❌ **You are already a member of a guild. You cannot create a new one.**")
    else:
        guild_creation_data[user_id] = {}
        await callback_query.message.reply_text("🛡️ **Please enter the name of your new guild:**")
    
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"join_guild"))
async def join_guild(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    existing_guild = await db.Guilds.find_one({"members": user_id})

    if existing_guild:
        await callback_query.message.reply_text("❌ **You are already a member of a guild. You cannot join another one.**")
    else:
        guild_join_data[user_id] = {}
        await callback_query.message.reply_text("⚔️ **Please enter the Guild ID of the guild you want to join:**")
    
    await callback_query.answer()


    # Handle other text messages as per your bot's functionality
