from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InputMediaPhoto
from ..database import db

async def get_character_details(image_id):
    character = await db.Characters.find_one({"id": image_id})
    return character

async def get_smode_preference(user_id):
    preference = await db.Preference.find_one({"user_id": user_id})
    if preference and "smode" in preference:
        return preference["smode"]
    else:
        return "Default"  # Return a default value if 'smode' is not found


async def set_fav(client: Client, message: Message):
    user_id = message.from_user.id

    if len(message.command) < 2:
        await message.reply("Please provide the character ID to set as favorite.")
        return

    fav_character_id = message.command[1]

    # Fetch the user's collection
    user_collection = await db.Collection.find_one({"user_id": user_id})

    if not user_collection or not any(image["image_id"] == fav_character_id for image in user_collection["images"]):
        await message.reply("You don't have this character in your collection.")
        return

    # Fetch the character details
    character = await get_character_details(fav_character_id)
    if not character or "img_url" not in character:
        await message.reply("Character details not found.")
        return

    # Send confirmation message with character image and inline buttons
    await client.send_photo(
        chat_id=message.chat.id,
        photo=character["img_url"],
        caption=f"Do you want to set {character['name']} as your favorite character?",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Confirm", callback_data=f"fav_confirm:{user_id}:{fav_character_id}"),
                    InlineKeyboardButton("Cancel", callback_data=f"fav_cancel:{user_id}")
                ]
            ]
        )
    )




async def unfav(client: Client, message: Message):
    user_id = message.from_user.id

    # Remove the favorite character
    await db.Preference.delete_one({"user_id": user_id})

    await message.reply("Favorite character removed successfully!")

async def get_fav_character(user_id):
    fav_entry = await db.Preference.find_one({"user_id": user_id})
    if fav_entry and "fav_character_id" in fav_entry:
        return fav_entry["fav_character_id"]
    else:
        return None

# Callback query handler for confirming favorite character
async def fav_confirm(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data.split(":")

    if len(data) != 3 or int(data[1]) != user_id:
        await callback_query.answer("🚫 This action is not for you.", show_alert=True)
        return

    fav_character_id = data[2]

    # Set the favorite character
    await db.Preference.update_one(
        {"user_id": user_id},
        {"$set": {"fav_character_id": fav_character_id}},
        upsert=True
    )

    # Edit the message to confirm the action
    character = await get_character_details(fav_character_id)
    await callback_query.message.edit_caption(
        caption=f"✨ **{character['name']}** has been set as your favorite character! 🎉",
        reply_markup=None
    )

    await callback_query.answer("✅ Favorite character set successfully!")


# Callback query handler for canceling the action
async def fav_cancel(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data.split(":")
    
    if len(data) != 2 or int(data[1]) != user_id:
        await callback_query.answer("This action is not for you.", show_alert=True)
        return

    # Edit the message to indicate the operation was canceled
    await callback_query.message.edit_caption(
        caption="Operation canceled.",
        reply_markup=None
    )

    await callback_query.answer("❌ Operation canceled.")




async def smode(client: Client, message: Message):
    user_id = message.from_user.id

    await message.reply(
        "🔧 **Customize your smashes interface using the buttons below:**",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🖼 Default", callback_data=f"smode_default:{user_id}")],
                [InlineKeyboardButton("🔢 Sort by Rarity", callback_data=f"smode_sort:{user_id}")],
                [InlineKeyboardButton("❌ Close", callback_data=f"smode_close:{user_id}")]
            ]
        )
    )


async def smode_default(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data.split(":")

    if len(data) != 2 or int(data[1]) != user_id:
        await callback_query.answer("🚫 **This action is not for you.**", show_alert=True)
        return

    # Update the smashes interface setting to default
    await db.Preference.update_one(
        {"user_id": user_id},
        {"$set": {"smode": "Default"}},
        upsert=True
    )

    # Edit the message to confirm the change
    await callback_query.message.edit_text(
        "**🔄 Your smashes interface has been set to: Default**",
        reply_markup=None
    )

    await callback_query.answer("✅ Smashes interface set to default.")


async def smode_sort(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data.split(":")

    if len(data) != 2 or int(data[1]) != user_id:
        await callback_query.answer("This action is not for you.", show_alert=True)
        return

    smode_preference = await get_smode_preference(user_id)

    await callback_query.message.edit_text(
        f"**Your Harem Sort Smashes is set to: {smode_preference}**",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🟡 Legendary", callback_data=f"smode_rarity:Legendary:{user_id}")],
                [InlineKeyboardButton("🟣 Rare", callback_data=f"smode_rarity:Rare:{user_id}")],
                [InlineKeyboardButton("🟢 Medium", callback_data=f"smode_rarity:Medium:{user_id}")],
                [InlineKeyboardButton("⚪️ Common", callback_data=f"smode_rarity:Common:{user_id}")],
                [InlineKeyboardButton("Close", callback_data=f"smode_close:{user_id}")]            
            ]
        )
    )

async def smode_rarity(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data.split(":")

    if len(data) != 3 or int(data[2]) != user_id:
        await callback_query.answer("This action is not for you.", show_alert=True)
        return

    rarity = data[1]

    await db.Preference.update_one(
        {"user_id": user_id},
        {"$set": {"smode": rarity}},
        upsert=True
    )

    await callback_query.message.edit_text(
        f"🔄 **Your smashes sort system has been successfully set to: {rarity}**",
        reply_markup=None
    )

    await callback_query.answer("Smashes sort system updated.")

async def smode_close(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data.split(":")

    if len(data) != 2 or int(data[1]) != user_id:
        await callback_query.answer("This action is not for you.", show_alert=True)
        return

    await callback_query.message.delete()

    await callback_query.answer("Operation canceled.")



async def set_cmode(client: Client, message: Message):
    user_id = message.from_user.id

    await client.send_message(
        chat_id=message.chat.id,
        text="**📝 Please select your caption mode:**",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔹 Caption 1", callback_data=f"cmode_select:{user_id}:Caption 1")],
                [InlineKeyboardButton("🔸 Caption 2", callback_data=f"cmode_select:{user_id}:Caption 2")],
                [InlineKeyboardButton("❌ Close", callback_data=f"cmode_close:{user_id}")]
            ]
        )
    )


async def cmode_select(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data.split(":")
    selected_mode = data[2]

    if int(data[1]) != user_id:
        await callback_query.answer("You are not authorized to perform this action.", show_alert=True)
        return

    await db.Preference.update_one(
        {"user_id": user_id},
        {"$set": {"icaption": selected_mode}},
        upsert=True
    )

    await callback_query.edit_message_text(
    f"**Your inline caption preference has been set to:**\n\n"
    f"**{selected_mode}** ✅"
)

async def cmode_close(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data.split(":")

    if int(data[1]) != user_id:
        await callback_query.answer("You are not authorized to perform this action.", show_alert=True)
        return

    await callback_query.message.delete()
