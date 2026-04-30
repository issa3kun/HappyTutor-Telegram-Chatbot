import gspread
from pymongo import MongoClient

GOOGLE_CREDS_FILE = "google credentials.json"
GOOGLE_SHEET_NAME = "bot tester"

client = MongoClient("mongodb://localhost:27017/")
db = client["tuition_bot"]
modules_collection = db["training_modules"]

gc = gspread.service_account(filename=GOOGLE_CREDS_FILE)
spreadsheet = gc.open(GOOGLE_SHEET_NAME)

modules_sheet = spreadsheet.worksheet("Modules")
questions_sheet = spreadsheet.worksheet("QuizQuestions")

module_rows = modules_sheet.get_all_records()
question_rows = questions_sheet.get_all_records()

questions_by_module = {}

for row in question_rows:
    module_id = int(row["module_id"])

    question_obj = {
        "question": row["question"],
        "options": [
            row["option1"],
            row["option2"],
            row["option3"],
            row["option4"]
        ],
        "correct_answer": int(row["correct_answer"])
    }

    if module_id not in questions_by_module:
        questions_by_module[module_id] = []

    questions_by_module[module_id].append(question_obj)

for row in module_rows:
    module_id = int(row["id"])

    module_doc = {
        "id": module_id,
        "title": row["title"],
        "content": row["content"],
        "resource_link": row["resource_link"],
        "pass_mark": int(row["pass_mark"]),
        "question_count": int(row["question_count"]),
        "quiz": questions_by_module.get(module_id, [])
    }

    modules_collection.update_one(
        {"id": module_id},
        {"$set": module_doc},
        upsert=True
    )

print("Training modules migrated to MongoDB successfully.")