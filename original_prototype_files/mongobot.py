from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["tuition_bot"]
test_collection = db["test"]
test_collection.insert_one({
    "message": "MongoDB is working!",
    "status": "success"
})

result = test_collection.find_one({"status": "success"})
print(result)