import os
import subprocess
import shutil
from pyrogram import Client
from pyrogram.types import Message
from ..config import MONGO_URL, OWNER_ID

def backup_db(path: str):
    try:
        subprocess.run(
            ["mongodump", "--uri", MONGO_URL, "--out", path],
            check=True
        )
        shutil.make_archive(path, 'zip', path)
        return f"{path}.zip"
    except subprocess.CalledProcessError as e:
        return f"Backup failed: {str(e)}"

def restore_db(zip_path: str):
    try:
        extract_path = zip_path.replace(".zip", "")
        shutil.unpack_archive(zip_path, extract_path)
        subprocess.run(
            ["mongorestore", "--uri", MONGO_URL, extract_path],
            check=True
        )
        return "Restore successful!"
    except (subprocess.CalledProcessError, shutil.ReadError) as e:
        return f"Restore failed: {str(e)}"

async def handle_backup(client: Client, message: Message):
    path = "./backup/WAIFU-BOT"
    zip_path = backup_db(path)
    if zip_path.endswith(".zip"):
        await client.send_document(chat_id=OWNER_ID, document=zip_path)
        shutil.rmtree(path)  # Clean up the backup directory
        os.remove(zip_path)  # Clean up the zip file
        response = "Backup successful!"
    else:
        response = zip_path
    await message.reply_text(response)

async def handle_restore(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("Please reply to a backup zip file to restore.")
        return
    
    document = message.reply_to_message.document
    file_path = await client.download_media(document.file_id)
    response = restore_db(file_path)
    os.remove(file_path)  # Clean up the downloaded zip file
    await message.reply_text(response)
