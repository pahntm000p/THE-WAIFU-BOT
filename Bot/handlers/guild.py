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
    await callback_query.message.delete()
    await callback_query.message.reply_text("🔄 **Please enter the user ID of the member you want to transfer ownership to:**")

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

@app.on_message(filters.text & filters.private)
async def handle_text(client: Client, message: Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id in guild_creation_data:
        if "guild_name" not in guild_creation_data[user_id]:
            guild_creation_data[user_id]["guild_name"] = text
            guild_id = await get_unique_guild_id()
            guild_creation_data[user_id]["guild_id"] = guild_id

            # Save the guild to the database
            await db.Guilds.insert_one({
                "guild_id": guild_id,
                "guild_name": text,
                "owner_id": user_id,
                "members": [user_id]
            })

            await message.reply_text(
                f"🏰 **Guild '{text}' created successfully!**\n"
                f"🔑 **Your Guild ID is:** `{guild_id}`\n"
                "🔗 **Share this ID with others to invite them to your guild.**"
            )
            del guild_creation_data[user_id]
        else:
            await message.reply_text("⚠️ **You have already created a guild. Please use the guild ID to invite others.**")
    elif user_id in guild_join_data:
        guild_id = text
        guild = await db.Guilds.find_one({"guild_id": guild_id})

        if guild:
            if user_id in guild['members']:
                await message.reply_text("⚠️ **You are already a member of this guild.**")
            else:
                # Add user to guild members
                await db.Guilds.update_one(
                    {"guild_id": guild_id},
                    {"$addToSet": {"members": user_id}}
                )
                await message.reply_text(f"✅ **You have successfully joined the guild '{guild['guild_name']}'!**")
        else:
            await message.reply_text("❌ **Invalid Guild ID. Please try again.**")
        
        del guild_join_data[user_id]
    elif user_id in guild_management_data:
        if guild_management_data[user_id] == "transfer_ownership":
            new_owner_id = int(text)
            new_owner_guild = await db.Guilds.find_one({"members": new_owner_id})

            if new_owner_guild and new_owner_guild['guild_id'] == (await db.Guilds.find_one({"owner_id": user_id}))['guild_id']:
                await db.Guilds.update_one(
                    {"owner_id": user_id},
                    {"$set": {"owner_id": new_owner_id}}
                )
                await message.reply_text(f"🔄 **Ownership has been transferred to user ID `{new_owner_id}` successfully!**")
            else:
                await message.reply_text("❌ **The user is not a member of your guild or is part of another guild. Please try again.**")

        del guild_management_data[user_id]
