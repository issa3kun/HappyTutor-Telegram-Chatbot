import json
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["tuition_bot"]
collection = db["user_progress"]

with open("progress.json", "r", encoding="utf-8") as file:
    progress_data = json.load(file)

user_progress = progress_data.get("user_progress", [])
completed_modules = progress_data.get("completed_modules", [])
all_user_ids = set(user_progress.keys()) | set(completed_modules.keys())

for telegram_id in all_user_ids:
    document = {
        "telegram_id": int(telegram_id),
        "current_progress": user_progress.get(telegram_id, []),
        "completed_modules": completed_modules.get(telegram_id, [])
    }
    
    collection.update_one(
        {"telegram_id": int(telegram_id)},
        {"$set": document},
        upsert=True
    )
print("Data migration completed successfully.")

