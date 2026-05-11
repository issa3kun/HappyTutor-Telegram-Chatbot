import bcrypt
from pymongo import MongoClient


client = MongoClient("mongodb://localhost:27017/")
db = client["tuition_bot"]

teachers_collection = db["teachers"]


def hash_password(password):
    password_bytes = password.encode("utf-8")
    hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed_password.decode("utf-8")


username = "test"
plain_password = "test123"
full_name = "Test Teacher"

teacher_account = {
    "username": username,
    "password_hash": hash_password(plain_password),
    "full_name": full_name,
    "role": "part_timer",
    "telegram_id": None,
    "is_active": True
}

teachers_collection.update_one(
    {"username": username},
    {"$set": teacher_account},
    upsert=True
)

print("Teacher account created successfully.")
print(f"Username: {username}")
print(f"Password: {plain_password}")