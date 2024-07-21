import random
from pyrogram import Client, filters
from ..database import get_random_image, update_drop, get_message_count, update_message_count
import requests
from io import BytesIO
import asyncio

lock = asyncio.Lock()

async def droptime(client: Client, message):
    if len(message.command) < 2:
        await message.reply("Please provide a message count.")
        return

    try:
        msg_count = int(message.command[1])
    except ValueError:
        await message.reply("Please provide a valid number for message count.")
        return

    group_id = message.chat.id

    await update_message_count(group_id, msg_count, 0)

    await message.reply(f"Random image will be dropped every {msg_count} messages in this group.")

async def check_message_count(client: Client, message):
    group_id = message.chat.id
    async with lock:
        count_doc = await get_message_count(group_id)

        if count_doc:
            current_count = count_doc["current_count"] + 1
            msg_count = count_doc["msg_count"]

            if current_count >= msg_count:
                current_count = 0
                # Get a random image URL from the database
                image_doc = await get_random_image()
                if not image_doc:
                    await client.send_message(group_id, "No images available to drop.")
                    return

                image_id = image_doc["id"]
                image_url = image_doc["img_url"]
                image_name = image_doc["name"]

                try:
                    response = requests.get(image_url)
                    response.raise_for_status()

                    image_data = BytesIO(response.content)
                    image_data.name = image_url.split("/")[-1]

                    # Store the last dropped image information
                    await update_drop(group_id, image_id, image_name, image_url)

                    # Send the image with the caption
                    caption = f"The new food has been served, Let's see who will smash first.\n**Smash using** : /smash name"
                    await client.send_photo(group_id, image_data, caption=caption)
                except requests.exceptions.RequestException as e:
                    await client.send_message(group_id, f"Failed to download the image: {e}")

            await update_message_count(group_id, msg_count, current_count)
