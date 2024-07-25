import motor.motor_asyncio
from .config import MONGO_URL
from datetime import datetime
from datetime import datetime, timedelta


client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client["WAIFU-BOT"]
db.Characters = db["Characters"]
db.Drops = db["Drops"]
db.MessageCounts = db["MessageCounts"]
db.Collection = db["Collection"]
db.Banned = db["Banned"]
db.Sudo = db["Sudo"]
db.Preference = db["Preference"]
db.Upreq = db["Upreq"]
db.Gtreq = db["Gtreq"]
db.Gtusers = db["Gtusers"]
db.Users = db["Users"]

async def get_character_details(image_id):
    return await db.Characters.find_one({"id": image_id})

async def get_next_id():
    counter = await db.Counters.find_one_and_update(
        {"_id": "character_id"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

async def get_random_image():
    current_time = datetime.utcnow()
    image = await db.Characters.aggregate([
        {
            "$match": {
                "$or": [
                    {"expiry_time": {"$exists": False}},
                    {"expiry_time": {"$gte": current_time}}
                ]
            }
        },
        {"$sample": {"size": 1}}
    ]).to_list(length=1)
    return image[0] if image else None


async def update_drop(group_id, image_id, image_name, image_url, smashed_by=None):
    await db.Drops.update_one(
        {"group_id": group_id},
        {"$set": {"image_id": image_id, "image_name": image_name, "image_url": image_url, "smashed_by": smashed_by}},
        upsert=True
    )

async def get_drop(group_id):
    return await db.Drops.find_one({"group_id": group_id})

async def update_smashed_image(user_id, image_id, user_name):
    # Find the user document
    user_doc = await db.Collection.find_one({"user_id": user_id})

    if user_doc:
        # Check if the image ID already exists in the user's collection
        image_found = False
        for image in user_doc.get("images", []):
            if image["image_id"] == image_id:
                image["count"] += 1
                image_found = True
                break
        
        # If the image ID is not found, add a new entry
        if not image_found:
            user_doc.setdefault("images", []).append({"image_id": image_id, "count": 1})
        
        await db.Collection.update_one(
            {"user_id": user_id},
            {"$set": {"images": user_doc["images"], "user_name": user_name}},
            upsert=True
        )
    else:
        # If the user document does not exist, create a new one
        await db.Collection.update_one(
            {"user_id": user_id},
            {"$set": {"images": [{"image_id": image_id, "count": 1}], "user_name": user_name}},
            upsert=True
        )
        
async def get_message_count(group_id):
    count_doc = await db.MessageCounts.find_one({"group_id": group_id})
    return count_doc

async def update_message_count(group_id, msg_count, current_count):
    await db.MessageCounts.update_one(
        {"group_id": group_id},
        {"$set": {"msg_count": msg_count, "current_count": current_count}},
        upsert=True
    )

async def get_user_collection(user_id):
    return await db.Collection.find_one({"user_id": user_id})

async def update_user_collection(user_id, updated_images):
    await db.Collection.update_one(
        {"user_id": user_id},
        {"$set": {"images": updated_images}},
        upsert=True
    )
    
async def get_all_images():
    characters = await db.Characters.find({}).to_list(length=None)
    return characters    


async def ban_user(user_id, duration_minutes=None):
    if duration_minutes:
        ban_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
    else:
        ban_until = None
    await db.Banned.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "ban_until": ban_until}},
        upsert=True
    )

async def unban_user(user_id):
    await db.Banned.delete_one({"user_id": user_id})

async def is_user_banned(user_id):
    ban_record = await db.Banned.find_one({"user_id": user_id})
    if ban_record:
        if ban_record["ban_until"] and ban_record["ban_until"] > datetime.utcnow():
            return True
        elif not ban_record["ban_until"]:
            return True
        else:
            await unban_user(user_id)
            return False
    return False

# Add user to Sudo collection
async def add_sudo_user(user_id):
    await db.Sudo.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id}},
        upsert=True
    )

# Remove user from Sudo collection
async def remove_sudo_user(user_id):
    await db.Sudo.delete_one({"user_id": user_id})

# Check if user is sudo
async def is_user_sudo(user_id):
    return await db.Sudo.find_one({"user_id": user_id}) is not None


