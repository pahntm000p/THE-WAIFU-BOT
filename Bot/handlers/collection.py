from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from ..database import db
from .preference import get_character_details, get_fav_character, get_smode_preference

async def smashes(client: Client, message: Message):
    user_id = message.from_user.id

    # Fetch the user's collection
    user_collection = await db.Collection.find_one({"user_id": user_id})

    if not user_collection or not user_collection.get("images"):
        await message.reply("You don't have any smashed characters yet.")
        return

    # Fetch the favorite character if set
    fav_character_id = await get_fav_character(user_id)

    # Fetch character details for each smashed image
    smode_preference = await get_smode_preference(user_id)

    sorted_images = []
    if smode_preference == "Default":
        sorted_images = user_collection["images"][:10]  # Default sorting
    else:
        for image in user_collection["images"]:
            character = await get_character_details(image["image_id"])
            if character and character.get("rarity") == smode_preference:
                sorted_images.append(image)
        sorted_images = sorted_images[:10]

    response_text = f"{message.from_user.first_name}'s Recent Collection:\n\n"
    for image in sorted_images:
        character = await get_character_details(image["image_id"])
        if character:
            response_text += (
                f"✨{character['name']} [x{image['count']}]\n"
                f"{character['rarity_sign']} | {character['rarity']} | {character['anime']}\n"
                "⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋\n"
            )

    # Determine which image URL to use (favorite or first in collection)
    img_url = None
    if fav_character_id:
        fav_character = await get_character_details(fav_character_id)
        if fav_character and any(image["image_id"] == fav_character_id for image in user_collection["images"]):
            img_url = fav_character["img_url"]

    if not img_url and user_collection["images"]:
        first_character = await get_character_details(user_collection["images"][0]["image_id"])
        if first_character and "img_url" in first_character:
            img_url = first_character["img_url"]

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