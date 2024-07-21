from pyrogram import Client, filters
from ..database import get_drop, update_smashed_image, update_drop
from pyrogram.types import Message

async def smash_image(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Please provide the character name.")
        return

    guessed_name = " ".join(message.command[1:]).strip().lower()
    group_id = message.chat.id
    user_id = message.from_user.id

    # Retrieve the last drop for the group
    drop = await get_drop(group_id)

    if not drop:
        await message.reply("No image has been dropped in this group.")
        return

    # Check if the image has already been smashed
    if drop["smashed_by"]:
        # Fetch the user who smashed the character
        smashed_user = await client.get_users(drop["smashed_by"])
        smashed_user_mention = smashed_user.mention if smashed_user else f"User ID: {drop['smashed_by']}"

        await message.reply(f"{smashed_user_mention} has already smashed this character!")
        return

    # Check if the guessed name is correct
    if guessed_name.lower() == drop["image_name"].strip().lower():
        # Update the smashed image in the user's collection
        await update_smashed_image(user_id, drop["image_id"], message.from_user.mention)
        
        # Update the drop to indicate it has been smashed
        await update_drop(group_id, drop["image_id"], drop["image_name"], drop["image_url"], smashed_by=user_id)

        await message.reply(f"Congratulations {message.from_user.mention}, you have smashed {drop['image_name']}!")
    else:
        await message.reply("Incorrect name. Try again!")

