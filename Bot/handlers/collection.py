from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from ..database import db

async def get_character_details(image_id):
    character = await db.Characters.find_one({"id": image_id})
    return character

async def smashes(client: Client, message: Message):
    user_id = message.from_user.id

    # Fetch the user's collection
    user_collection = await db.Collection.find_one({"user_id": user_id})

    if not user_collection or not user_collection.get("images"):
        await message.reply("You don't have any smashed characters yet.")
        return

    # Fetch character details for each smashed image
    response_text = f"{message.from_user.first_name}'s Recent Collection:\n\n"
    for image in user_collection["images"][:10]:  # Limit to 10 entries
        character = await get_character_details(image["image_id"])
        if character:
            response_text += (
                f"✨{character['name']} [x{image['count']}]\n"
                f"{character['rarity_sign']} | {character['rarity']} | {character['anime']}\n"
                "⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋\n"
            )

    # Get the first character's image URL
    first_character = await get_character_details(user_collection["images"][0]["image_id"])
    if first_character and "img_url" in first_character:
        img_url = first_character["img_url"]
    else:
        img_url = None

    # Send the image with the user's collection as the caption
    if img_url:
        await client.send_photo(
            chat_id=message.chat.id,
            photo=img_url,
            caption=response_text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Smashes", switch_inline_query_current_chat=f"smashed.{user_id}"
                        )
                    ]
                ]
            )
        )
    else:
        await message.reply(response_text, reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Smashes", switch_inline_query_current_chat=f"smashed.{user_id}"
                    )
                ]
            ]
        ))


