# ============================================================
# Happy Tutors Telegram Training Bot
# ============================================================
# Purpose:
# This bot helps part-time tuition teachers complete onboarding
# and training modules through Telegram.
#
# Current database:
# - MongoDB is the main database.
# - Training modules, quiz questions, user progress, daily tasks,
#   and contact information are all loaded from MongoDB.
#
# Main MongoDB database:
# - tuition_bot
#
# Main collections:
# - user_progress
# - training_modules
# - daily_tasks
# - contacts
#
# Notes for future interns:
# - Do not edit bot logic unless you are changing features.
# - To update training content, edit MongoDB collections.
# - Original prototype files are stored in original_prototype_files.
# ============================================================

import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from pymongo import MongoClient


# ============================================================
# DATABASE SETUP
# ============================================================

client = MongoClient("mongodb://localhost:27017/")
db = client["tuition_bot"]

progress_collection = db["user_progress"]
modules_collection = db["training_modules"]
daily_tasks_collection = db["daily_tasks"]
contacts_collection = db["contacts"]
# ============================================================
# BOT TOKEN
# ============================================================

TOKEN = "8575673781:AAGGzNVekx8UQdcaHzcCL9mDva3Fou2DV0o"

# ============================================================
# DATA LOADING FUNCTIONS
# ============================================================

def load_training_modules_from_mongo():
    """
    Loads all training modules from MongoDB.
    The modules are sorted by their id so they appear in the correct order.
    """
    return list(modules_collection.find({}, {"_id": 0}).sort("id", 1))


def load_data():
    daily_tasks = daily_tasks_collection.find_one(
        {"type": "daily_tasks"},
        {"_id": 0}
    )

    contacts = contacts_collection.find_one(
        {"type": "contacts"},
        {"_id": 0}
    )

    return {
        "training_modules": load_training_modules_from_mongo(),
        "daily_tasks": daily_tasks or {
            "default": [],
            "first_day": []
        },
        "contacts": contacts or {
            "coordinator": "",
            "admin": ""
        }
    }


def find_module(data, module_id):
    """
    Finds one module by its id.
    Returns None if the module cannot be found.
    """
    return next(
        (module for module in data["training_modules"] if module["id"] == module_id),
        None
    )


def build_module_text(module):
    """
    Creates the text shown when a user opens a module.
    """
    return (
        f"{module['title']}\n\n"
        f"{module['content']}\n\n"
        f"Resource: {module['resource_link']}"
    )


# ============================================================
# USER PROGRESS FUNCTIONS
# ============================================================

def get_user_record(user_id):
    """
    Gets the user's progress record from MongoDB.
    If the user does not exist yet, a new record is created.
    """
    user_id = int(user_id)

    record = progress_collection.find_one({"telegram_id": user_id})

    if record:
        return record

    new_record = {
        "telegram_id": user_id,
        "current_progress": None,
        "completed_modules": []
    }

    progress_collection.insert_one(new_record)
    return new_record


def get_current_progress(user_id):
    """
    Gets the user's current quiz progress.
    Returns None if there is no quiz in progress.
    """
    record = get_user_record(user_id)
    progress = record.get("current_progress")

    if isinstance(progress, dict):
        return progress

    return None


def set_current_progress(user_id, progress):
    """
    Saves or updates the user's current quiz progress.
    """
    progress_collection.update_one(
        {"telegram_id": int(user_id)},
        {
            "$set": {
                "telegram_id": int(user_id),
                "current_progress": progress
            },
            "$setOnInsert": {
                "completed_modules": []
            }
        },
        upsert=True
    )


def clear_current_progress(user_id):
    """
    Clears the user's current quiz progress after the quiz ends.
    """
    progress_collection.update_one(
        {"telegram_id": int(user_id)},
        {"$set": {"current_progress": None}},
        upsert=True
    )


def get_completed_modules(user_id):
    """
    Returns a list of module ids that the user has completed.
    """
    record = get_user_record(user_id)
    return record.get("completed_modules", [])


def add_completed_module(user_id, module_id):
    """
    Marks a module as completed.
    $addToSet prevents duplicate module ids from being added.
    """
    progress_collection.update_one(
        {"telegram_id": int(user_id)},
        {
            "$set": {
                "telegram_id": int(user_id)
            },
            "$addToSet": {
                "completed_modules": int(module_id)
            },
            "$setOnInsert": {
                "current_progress": None
            }
        },
        upsert=True
    )


# ============================================================
# MENU / KEYBOARD FUNCTIONS
# ============================================================

def create_keyboard(buttons):
    """
    Helper function to create an InlineKeyboardMarkup.

    Example input:
    [
        [("Button Text", "callback_data")],
        [("Another Button", "another_callback")]
    ]
    """
    keyboard = []

    for row in buttons:
        keyboard_row = []

        for text, callback_data in row:
            keyboard_row.append(
                InlineKeyboardButton(text, callback_data=callback_data)
            )

        keyboard.append(keyboard_row)

    return InlineKeyboardMarkup(keyboard)


def get_main_menu():
    return create_keyboard([
        [("Today's Tasks", "today_tasks")],
        [("First Day Guide", "first_day")],
        [("Mandatory Modules", "modules")],
        [("Resume Training", "resume_training")],
        [("My Progress", "my_progress")],
        [("Who to Contact", "contacts")]
    ])


def get_secondary_menu():
    return create_keyboard([
        [("Main Menu", "main_menu")]
    ])


def get_module_menu(data, user_id):
    """
    Shows all modules.

    Module 1 is always unlocked.
    Other modules unlock only after the previous module is completed.
    """
    completed_modules = get_completed_modules(user_id)
    keyboard = []

    for module in data["training_modules"]:
        module_id = module["id"]
        module_title = module["title"]

        is_unlocked = module_id == 1 or (module_id - 1) in completed_modules

        if is_unlocked:
            button_text = module_title
            callback_data = f"module_{module_id}"
        else:
            button_text = f"{module_title} 🔒"
            callback_data = f"locked_module_{module_id}"

        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=callback_data)
        ])

    keyboard.append([
        InlineKeyboardButton("Main Menu", callback_data="main_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_quiz_start_menu(module_id):
    return create_keyboard([
        [("Start Quiz", f"start_quiz_{module_id}")],
        [("Main Menu", "main_menu")]
    ])


def get_question_keyboard(options, module_id, question_index):
    """
    Creates answer buttons for a quiz question.
    """
    keyboard = []

    for option_index, option_text in enumerate(options):
        keyboard.append([
            InlineKeyboardButton(
                option_text,
                callback_data=f"answer_{module_id}_{question_index}_{option_index}"
            )
        ])

    return InlineKeyboardMarkup(keyboard)


def get_retry_menu(module_id):
    return create_keyboard([
        [("Retry Quiz", f"start_quiz_{module_id}")],
        [("Main Menu", "main_menu")]
    ])


# ============================================================
# MESSAGE HELPERS
# ============================================================

async def send_main_menu(message):
    await message.reply_text(
        "Welcome to the Teacher Support Bot.\nChoose an option below:",
        reply_markup=get_main_menu()
    )


async def send_numbered_list(message, title, items):
    text = title + "\n\n"

    for index, item in enumerate(items, start=1):
        text += f"{index}. {item}\n"

    await message.reply_text(
        text=text,
        reply_markup=get_secondary_menu()
    )


async def send_module_content(message, module):
    await message.reply_text(
        text=build_module_text(module),
        reply_markup=get_quiz_start_menu(module["id"])
    )


# ============================================================
# BOT COMMANDS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /start command.

    Supports:
    /start onboarding
    /start module1
    /start
    """
    data = load_data()
    message = update.effective_message

    if context.args:
        payload = context.args[0]

        if payload == "onboarding":
            await message.reply_text(
                "Welcome to teacher onboarding.\nChoose an option below:",
                reply_markup=get_main_menu()
            )
            return

        if payload == "module1":
            module = find_module(data, 1)

            if module:
                await send_module_content(message, module)
                return

    await send_main_menu(message)


# ============================================================
# BUTTON ACTIONS
# ============================================================

async def handle_resume_training(query, data, user_id):
    progress = get_current_progress(user_id)

    if not progress:
        await query.message.reply_text(
            text="You have no training in progress right now.",
            reply_markup=get_secondary_menu()
        )
        return

    module_id = progress["module_id"]
    question_index = progress["question_index"]
    module = find_module(data, module_id)

    if not module:
        await query.message.reply_text(
            text="Sorry, this module could not be found.",
            reply_markup=get_secondary_menu()
        )
        return

    current_question = progress["questions"][question_index]

    await query.message.reply_text(
        text=(
            f"Resuming {module['title']}\n\n"
            f"Q{question_index + 1}. {current_question['question']}"
        ),
        reply_markup=get_question_keyboard(
            current_question["options"],
            module_id,
            question_index
        )
    )


async def handle_my_progress(query, data, user_id):
    completed_modules = get_completed_modules(user_id)
    module_lines = []

    for module in data["training_modules"]:
        if module["id"] in completed_modules:
            status = "Completed"
        else:
            status = "Not completed"

        module_lines.append(f"{module['title']}: {status}")

    all_modules_completed = len(completed_modules) == len(data["training_modules"])
    overall_status = "Cleared" if all_modules_completed else "Not cleared"

    text = "My Progress:\n\n"
    text += "\n".join(module_lines)
    text += f"\n\nOverall status: {overall_status}"

    await query.message.reply_text(
        text=text,
        reply_markup=get_secondary_menu()
    )


async def handle_contacts(query, data):
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


async def handle_start_quiz(query, data, user_id, module_id):
    module = find_module(data, module_id)

    if not module:
        await query.message.reply_text(
            text="Sorry, this module could not be found.",
            reply_markup=get_secondary_menu()
        )
        return

    question_count = module.get("question_count", len(module["quiz"]))

    selected_questions = random.sample(
        module["quiz"],
        question_count
    )

    progress = {
        "module_id": module_id,
        "question_index": 0,
        "score": 0,
        "questions": selected_questions
    }

    set_current_progress(user_id, progress)

    first_question = selected_questions[0]

    await query.message.reply_text(
        text=f"Quiz Started: {module['title']}\n\nQ1. {first_question['question']}",
        reply_markup=get_question_keyboard(
            first_question["options"],
            module_id,
            0
        )
    )


async def handle_answer(query, data, user_id):
    """
    Handles the user's selected quiz answer.
    Then either sends the next question or shows the final result.
    """
    parts = query.data.split("_")

    module_id = int(parts[1])
    question_index = int(parts[2])
    selected_option = int(parts[3])

    module = find_module(data, module_id)
    progress = get_current_progress(user_id)

    if not module or not progress:
        await query.message.reply_text(
            text="Sorry, I could not find your quiz progress. Please start the quiz again.",
            reply_markup=get_secondary_menu()
        )
        return

    current_question = progress["questions"][question_index]

    if selected_option == current_question["correct_answer"]:
        progress["score"] += 1

    progress["question_index"] += 1
    set_current_progress(user_id, progress)

    next_question_index = progress["question_index"]

    if next_question_index < len(progress["questions"]):
        next_question = progress["questions"][next_question_index]

        await query.message.reply_text(
            text=f"Q{next_question_index + 1}. {next_question['question']}",
            reply_markup=get_question_keyboard(
                next_question["options"],
                module_id,
                next_question_index
            )
        )
        return

    await finish_quiz(query, user_id, module, progress)


async def finish_quiz(query, user_id, module, progress):
    """
    Shows the final quiz result.
    If the user passes, the module is marked as completed.
    If not, the user can retry.
    """
    module_id = module["id"]
    score = progress["score"]
    total = len(progress["questions"])
    pass_mark = module["pass_mark"]

    if score >= pass_mark:
        add_completed_module(user_id, module_id)

        result_text = (
            f"You scored {score}/{total}.\n\n"
            f"Congratulations! You passed the quiz.\n"
            f"Module {module_id + 1} unlocked."
        )
        reply_markup = get_secondary_menu()

    else:
        result_text = (
            f"You scored {score}/{total}.\n\n"
            f"You did not pass. Please review the module and try again."
        )
        reply_markup = get_retry_menu(module_id)

    clear_current_progress(user_id)

    await query.message.reply_text(
        text=result_text,
        reply_markup=reply_markup
    )


# ============================================================
# MAIN BUTTON HANDLER
# ============================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles all button clicks from the Telegram inline keyboard.
    """
    query = update.callback_query
    await query.answer()

    data = load_data()
    user_id = query.from_user.id
    action = query.data

    if action == "main_menu":
        await send_main_menu(query.message)
        return

    if action == "today_tasks":
        await send_numbered_list(
            query.message,
            "Today's Tasks:",
            data["daily_tasks"]["default"]
        )
        return

    if action == "first_day":
        await send_numbered_list(
            query.message,
            "First Day Guide:",
            data["daily_tasks"]["first_day"]
        )
        return

    if action == "modules":
        await query.message.reply_text(
            text="Mandatory Beginner Modules:\nChoose a module below:",
            reply_markup=get_module_menu(data, user_id)
        )
        return

    if action == "resume_training":
        await handle_resume_training(query, data, user_id)
        return

    if action == "my_progress":
        await handle_my_progress(query, data, user_id)
        return

    if action == "contacts":
        await handle_contacts(query, data)
        return

    if action.startswith("locked_module_"):
        await query.message.reply_text(
            text="This module is still locked. Please complete the previous module first.",
            reply_markup=get_secondary_menu()
        )
        return

    if action.startswith("module_"):
        module_id = int(action.split("_")[1])
        module = find_module(data, module_id)

        if module:
            await send_module_content(query.message, module)

        return

    if action.startswith("start_quiz_"):
        module_id = int(action.split("_")[2])
        await handle_start_quiz(query, data, user_id, module_id)
        return

    if action.startswith("answer_"):
        await handle_answer(query, data, user_id)
        return


# ============================================================
# RUN THE BOT
# ============================================================

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()