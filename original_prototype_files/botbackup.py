import gspread
import random
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from pymongo import MongoClient


TOKEN = "8575673781:AAGGzNVekx8UQdcaHzcCL9mDva3Fou2DV0o"
GOOGLE_CREDS_FILE = "google credentials.json"
GOOGLE_SHEET_NAME = "bot tester"
PROGRESS_FILE = "progress.json"
user_progress = {}
completed_modules = {}

def load_training_modules_from_sheets():
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

    training_modules = []
    for row in module_rows:
        module_id = int(row["id"])

        training_modules.append({
            "id": module_id,
            "title": row["title"],
            "content": row["content"],
            "resource_link": row["resource_link"],
            "pass_mark": int(row["pass_mark"]),
            "question_count": int(row["question_count"]),
            "quiz": questions_by_module.get(module_id, [])
        })

    return training_modules

def load_data():
    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    data["training_modules"] = load_training_modules_from_sheets()
    return data

def load_progress():
    global user_progress, completed_modules

    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            user_progress = {int(k): v for k, v in data.get("user_progress", {}).items()}
            completed_modules = {int(k): v for k, v in data.get("completed_modules", {}).items()}
    except FileNotFoundError:
        user_progress = {}
        completed_modules = {}

def save_progress():
    data = {
        "user_progress": {str(k): v for k, v in user_progress.items()},
        "completed_modules": {str(k): v for k, v in completed_modules.items()}
    }

    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("Today's Tasks", callback_data="today_tasks")],
        [InlineKeyboardButton("First Day Guide", callback_data="first_day")],
        [InlineKeyboardButton("Mandatory Modules", callback_data="modules")],
        [InlineKeyboardButton("Resume Training", callback_data="resume_training")],
        [InlineKeyboardButton("My Progress", callback_data="my_progress")],
        [InlineKeyboardButton("Who to Contact", callback_data="contacts")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_secondary_menu():
    keyboard = [
        [InlineKeyboardButton("Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_module_menu(data, user_id):
    keyboard = []
    completed = completed_modules.get(user_id, [])

    for module in data["training_modules"]:
        if module["id"] == 1 or (module["id"] - 1) in completed:
            keyboard.append([
                InlineKeyboardButton(module["title"], callback_data=f"module_{module['id']}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(f"{module['title']} 🔒", callback_data=f"locked_module_{module['id']}")
            ])

    keyboard.append([
        InlineKeyboardButton("Main Menu", callback_data="main_menu")
    ])
    return InlineKeyboardMarkup(keyboard)


def get_quiz_start_menu(module_id):
    keyboard = [
        [InlineKeyboardButton("Start Quiz", callback_data=f"start_quiz_{module_id}")],
        [InlineKeyboardButton("Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_question_keyboard(options, module_id, question_index):
    keyboard = []
    for i, option in enumerate(options):
        keyboard.append([
            InlineKeyboardButton(option, callback_data=f"answer_{module_id}_{question_index}_{i}")
        ])
    return InlineKeyboardMarkup(keyboard)


def get_retry_menu(module_id):
    keyboard = [
        [InlineKeyboardButton("Retry Quiz", callback_data=f"start_quiz_{module_id}")],
        [InlineKeyboardButton("Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()

    if context.args:
        payload = context.args[0]

        if payload == "onboarding":
            await update.effective_message.reply_text(
                "Welcome to teacher onboarding.\nChoose an option below:",
                reply_markup=get_main_menu()
            )
            return

        elif payload == "module1":
            module = next((m for m in data["training_modules"] if m["id"] == 1), None)

            if module:
                text = (
                    f"{module['title']}\n\n"
                    f"{module['content']}\n\n"
                    f"Resource: {module['resource_link']}"
                )
                await update.effective_message.reply_text(
                    text=text,
                    reply_markup=get_quiz_start_menu(1)
                )
                return

    await update.effective_message.reply_text(
        "Welcome to the Teacher Support Bot.\nChoose an option below:",
        reply_markup=get_main_menu()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    user_id = query.from_user.id

    if query.data == "main_menu":
        await query.message.reply_text(
            "Welcome to the Teacher Support Bot.\nChoose an option below:",
            reply_markup=get_main_menu()
        )

    elif query.data == "today_tasks":
        tasks = data["daily_tasks"]["default"]
        text = "Today's Tasks:\n\n" + "\n".join(
            f"{i+1}. {task}" for i, task in enumerate(tasks)
        )
        await query.message.reply_text(
            text=text,
            reply_markup=get_secondary_menu()
        )

    elif query.data == "first_day":
        tasks = data["daily_tasks"]["first_day"]
        text = "First Day Guide:\n\n" + "\n".join(
            f"{i+1}. {task}" for i, task in enumerate(tasks)
        )
        await query.message.reply_text(
            text=text,
            reply_markup=get_secondary_menu()
        )

    elif query.data == "modules":
        await query.message.reply_text(
            text="Mandatory Beginner Modules:\nChoose a module below:",
            reply_markup=get_module_menu(data, user_id)
        )

    elif query.data == "resume_training":
        if user_id not in user_progress:
            await query.message.reply_text(
                text="You have no training in progress right now.",
                reply_markup=get_secondary_menu()
            )
        else:
            module_id = user_progress[user_id]["module_id"]
            question_index = user_progress[user_id]["question_index"]
            module = next((m for m in data["training_modules"] if m["id"] == module_id), None)

            if module:
                current_question = user_progress[user_id]["questions"][question_index]
                await query.message.reply_text(
                    text=f"Resuming {module['title']}\n\nQ{question_index + 1}. {current_question['question']}",
                    reply_markup=get_question_keyboard(current_question["options"], module_id, question_index)
                )

    elif query.data == "my_progress":
        completed = completed_modules.get(user_id, [])
        module_lines = []

        for module in data["training_modules"]:
            status = "Completed" if module["id"] in completed else "Not completed"
            module_lines.append(f"{module['title']}: {status}")

        all_completed = len(completed) == len(data["training_modules"])
        overall_status = "Cleared" if all_completed else "Not cleared"

        text = "My Progress:\n\n" + "\n".join(module_lines)
        text += f"\n\nOverall status: {overall_status}"

        await query.message.reply_text(
            text=text,
            reply_markup=get_secondary_menu()
        )

    elif query.data == "contacts":
        contacts = data["contacts"]
        text = (
            "Who to Contact:\n\n"
            f"{contacts['coordinator']}\n"
            f"{contacts['admin']}"
        )
        await query.message.reply_text(
            text=text,
            reply_markup=get_secondary_menu()
        )

    elif query.data.startswith("locked_module_"):
        await query.message.reply_text(
            text="This module is still locked. Please complete the previous module first.",
            reply_markup=get_secondary_menu()
        )

    elif query.data.startswith("module_"):
        module_id = int(query.data.split("_")[1])
        module = next((m for m in data["training_modules"] if m["id"] == module_id), None)

        if module:
            text = (
                f"{module['title']}\n\n"
                f"{module['content']}\n\n"
                f"Resource: {module['resource_link']}"
            )
            await query.message.reply_text(
                text=text,
                reply_markup=get_quiz_start_menu(module_id)
            )

    elif query.data.startswith("start_quiz_"):
        module_id = int(query.data.split("_")[2])
        module = next((m for m in data["training_modules"] if m["id"] == module_id), None)

        if module:
            question_count = module.get("question_count", len(module["quiz"]))
            selected_questions = random.sample(module["quiz"], question_count)

            user_progress[user_id] = {
                "module_id": module_id,
                "question_index": 0,
                "score": 0,
                "questions": selected_questions
            }
            save_progress()

            question = selected_questions[0]
            await query.message.reply_text(
                text=f"Quiz Started: {module['title']}\n\nQ1. {question['question']}",
                reply_markup=get_question_keyboard(question["options"], module_id, 0)
            )

    elif query.data.startswith("answer_"):
        parts = query.data.split("_")
        module_id = int(parts[1])
        question_index = int(parts[2])
        selected_option = int(parts[3])

        module = next((m for m in data["training_modules"] if m["id"] == module_id), None)

        if module and user_id in user_progress:
            current_question = user_progress[user_id]["questions"][question_index]

            if selected_option == current_question["correct_answer"]:
                user_progress[user_id]["score"] += 1

            user_progress[user_id]["question_index"] += 1
            save_progress()
            next_index = user_progress[user_id]["question_index"]

            if next_index < len(user_progress[user_id]["questions"]):
                next_question = user_progress[user_id]["questions"][next_index]
                await query.message.reply_text(
                    text=f"Q{next_index + 1}. {next_question['question']}",
                    reply_markup=get_question_keyboard(next_question["options"], module_id, next_index)
                )
            else:
                score = user_progress[user_id]["score"]
                total = len(user_progress[user_id]["questions"])
                pass_mark = module["pass_mark"]

                if score >= pass_mark:
                    if user_id not in completed_modules:
                        completed_modules[user_id] = []

                    if module_id not in completed_modules[user_id]:
                        completed_modules[user_id].append(module_id)
                    save_progress()

                    result_text = (
                        f"You scored {score}/{total}.\n\n"
                        f"Congratulations! You passed the quiz."
                        f" Module 2 unlocked."
                    )
                    reply_markup = get_secondary_menu()
                else:
                    result_text = (
                        f"You scored {score}/{total}.\n\n"
                        f"You did not pass. Please review the module and try again."
                    )
                    reply_markup = get_retry_menu(module_id)

                del user_progress[user_id]
                save_progress()

                await query.message.reply_text(
                    text=result_text,
                    reply_markup=reply_markup
                )


def main():
    load_progress()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()