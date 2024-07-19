import motor.motor_asyncio
from .config import MONGO_URL

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client["WAIFU-BOT"]
db.Characters = db["Characters"]
db.Counters = db["Counters"]
db.MessageCounts = db["MessageCounts"]
db.LastDroppedImage = db["LastDroppedImage"]

async def get_next_id():
    counter = await db.Counters.find_one_and_update(
        {"_id": "character_id"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

async def update_msg_count(chat_id, reset=False):
    if reset:
        await db.MessageCounts.update_one({"chat_id": chat_id}, {"$set": {"count": 0}}, upsert=True)
        return 0

    result = await db.MessageCounts.find_one_and_update(
        {"chat_id": chat_id},
        {"$inc": {"count": 1}},
        return_document=True
    )
    if result is None:
        await db.MessageCounts.insert_one({"chat_id": chat_id, "count": 1})
        return 1

    return result["count"]

async def set_droptime(chat_id, msg_count):
    await db.MessageCounts.update_one({"chat_id": chat_id}, {"$set": {"droptime": msg_count}}, upsert=True)

async def get_droptime(chat_id):
    result = await db.MessageCounts.find_one({"chat_id": chat_id})
    if result and "droptime" in result:
        return result["droptime"]
    return 100

async def get_random_image():
    character = await db.Characters.aggregate([{"$sample": {"size": 1}}]).to_list(length=1)
    return character[0] if character else None

async def update_last_dropped_image(chat_id, character):
    character_data = {k: v for k, v in character.items() if k != "_id"}
    await db.LastDroppedImage.update_one(
        {"chat_id": chat_id},
        {"$set": character_data},
        upsert=True
    )

async def get_last_dropped_image(chat_id):
    return await db.LastDroppedImage.find_one({"chat_id": chat_id})
