import json
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["tuition_bot"]

daily_tasks_collection = db["daily_tasks"]
contacts_collection = db["contacts"]

with open("data.json", "r", encoding="utf-8") as file:
    data = json.load(file)

daily_tasks = data.get("daily_tasks", {})
contacts = data.get("contacts", {})

daily_tasks_collection.update_one(
    {"type": "daily_tasks"},
    {
        "$set": {
            "type": "daily_tasks",
            "default": daily_tasks.get("default", []),
            "first_day": daily_tasks.get("first_day", [])
        }
    },
    upsert=True
)

contacts_collection.update_one(
    {"type": "contacts"},
    {
        "$set": {
            "type": "contacts",
            "coordinator": contacts.get("coordinator", ""),
            "admin": contacts.get("admin", "")
        }
    },
    upsert=True
)

print("Daily tasks and contacts migrated to MongoDB successfully.")