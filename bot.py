from keep_alive import keep_alive
keep_alive()
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from config import BOT_TOKEN
from data_manager import load_tasks, load_users, save_users, load_tests
import random
# Глобальное хранилище состояний
user_state = {}

# Приветствие
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_state[user_id] = {"prev_menu": "start"}

    keyboard = [["🎯 Подготовка к поступлению в 7 класс"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Готово! Подготовка к поступлению в РФМШ начинается! 🎯\n"
        "Сейчас доступна программа для 7 класса —\n"
        "разделы для 8 и 9 классов появятся позже. ⏳\n\n"
        "👇 Выбери класс, чтобы начать:",
        reply_markup=markup
    )

# Главное меню и логика выбора
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    print(f"[DEBUG] User: {user_id} | Text: {text} | Prev: {user_state.get(user_id, {}).get('prev_menu')} | Mode: {user_state.get(user_id, {}).get('mode')}")

    users_data = load_users()
    if str(user_id) not in users_data:
        users_data[str(user_id)] = {}

    # Универсальная кнопка Назад
    if text == "⬅️ Назад":
        prev = user_state.get(user_id, {}).get("prev_menu")

        if prev == "start":
            keyboard = [["🎯 Подготовка к поступлению в 7 класс"]]
            markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("⬅️", reply_markup=markup)
            user_state[user_id] = {"prev_menu": None, "mode": None}
            return

        elif prev == "main_menu":
            menu_buttons = [
                ["📂 Задачи по темам", "🧪 Полные тесты"],
                ["📊 Проверить прогресс", "🧠 Что решать дальше?"],
                ["🔥 Задача дня", "ℹ️ Информация об экзамене"],
                ["⬅️ Назад"]
            ]
            markup = ReplyKeyboardMarkup(menu_buttons, resize_keyboard=True)
            await update.message.reply_text("⬅️", reply_markup=markup)
            user_state[user_id] = {"prev_menu": "start", "mode": None}
            return

        elif prev == "topics":
            tasks = load_tasks()
            topic_buttons = [[topic.capitalize()] for topic in tasks.keys()]
            topic_buttons.append(["⬅️ Назад"])
            markup = ReplyKeyboardMarkup(topic_buttons, resize_keyboard=True)
            await update.message.reply_text("⬅️ Возврат к выбору темы:", reply_markup=markup)

            user_state[user_id] = {
                "mode": "choosing_topic",
                "prev_menu": "main_menu"
            }
            return
    # --- ОТПРАВИТЬ ОТВЕТ ---
    if text == "✅ Отправить ответ" and user_state.get(user_id, {}).get("mode") != "daily_solving" and user_state.get(user_id, {}).get("mode") != "daily_waiting":
        await update.message.reply_text("✏️ Введи свой ответ на задачу:")
        user_state[user_id]["mode"] = "awaiting_answer"
        return

    # --- ОБРАБОТКА ВВОДА ОТВЕТА ---
    if user_state.get(user_id, {}).get("mode") == "awaiting_answer":
        topic = user_state[user_id].get("topic")
        task_id = user_state[user_id].get("task_id")
        task_data = load_tasks().get(topic, {})
        task = next((t for t in task_data.get("tasks", []) if t["id"] == task_id), None)

        if task:
            if text.strip().lower() == task["answer"].strip().lower():
                await update.message.reply_text("✅ Правильно! Отличная работа 💪")
                user_state[user_id]["mode"] = "choosing_task"

                # Сохраняем как решённую (если используешь users_data)
                if topic not in users_data[str(user_id)]:
                    users_data[str(user_id)][topic] = {}
                users_data[str(user_id)][topic][str(task_id)] = "solved"
                save_users(users_data)


                # Возврат к списку задач по теме
                task_buttons = [[f"№ {t['id']}"] for t in task_data.get("tasks", [])]
                task_buttons.append(["⬅️ Назад"])
                markup = ReplyKeyboardMarkup(task_buttons, resize_keyboard=True)
                await update.message.reply_text(
                    f"📚 Тема: *{topic}*\nВыбери номер задачи:",
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
            else:
                buttons = [["🔁 Попробовать снова"], ["🧮 Посмотреть решение"], ["🚫 Отметить как не решённую"]]
                markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
                await update.message.reply_text(
                    "❌ Неправильно. Попробуй ещё раз, посмотри решение или отметь как не решённую.",
                    reply_markup=markup
                )
                user_state[user_id]["mode"] = "after_wrong_answer"
        return
        # --- ОБРАБОТКА КНОПОК В РЕЖИМЕ solving_task ---
    elif user_state.get(user_id, {}).get("mode") == "solving_task":
        topic = user_state[user_id].get("topic")
        task_id = user_state[user_id].get("task_id")
        task_data = load_tasks().get(topic, {})
        task = next((t for t in task_data.get("tasks", []) if t["id"] == task_id), None)

        if not task:
            await update.message.reply_text("❗ Задача не найдена.")
            return

        if text == "🧠 Объяснение темы":
            topic_explanation = task_data.get("explanation")
            if topic_explanation:
                await update.message.reply_text(f"🧠 Объяснение по теме *{topic}*:\n{topic_explanation}", parse_mode="Markdown")
            else:
                await update.message.reply_text("🔍 Объяснение темы пока не добавлено.")
            return

        elif text == "🧮 Объяснение решения":
            explanation = task.get("explanation", "❗ Объяснение пока не добавлено.")
            await update.message.reply_text(f"🧮 Объяснение:\n{explanation}")
            return

    # --- ПОСЛЕ НЕПРАВИЛЬНОГО ОТВЕТА ---
    if user_state.get(user_id, {}).get("mode") == "after_wrong_answer":
        if text == "🔁 Попробовать снова":
            task_id = user_state[user_id].get("task_id")
            topic = user_state[user_id].get("topic")
            task_data = load_tasks().get(topic, {})
            task = next((t for t in task_data.get("tasks", []) if t["id"] == task_id), None)

            if task:
                buttons = [
                    ["🧠 Объяснение темы", "🧮 Объяснение решения"],
                    ["✅ Отправить ответ"],
                    ["⬅️ Назад"]
                ]
                markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
                await update.message.reply_text(
                    f"📌 Задача {task['id']}:\n{task['question']}",
                    reply_markup=markup
                )
                user_state[user_id]["mode"] = "solving_task"
            return

        elif text == "🧮 Посмотреть решение":
            topic = user_state[user_id].get("topic")
            task_id = user_state[user_id].get("task_id")
            task_data = load_tasks().get(topic, {})
            task = next((t for t in task_data.get("tasks", []) if t["id"] == task_id), None)

            if task:
                await update.message.reply_text(f"📘 Объяснение:\n{task['explanation']}")

                # Показываем снова условие и выбор
                buttons = [
                    ["🧠 Объяснение темы", "🧮 Объяснение решения"],
                    ["✅ Отправить ответ"],
                    ["⬅️ Назад"]
                ]
                markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
                await update.message.reply_text(
                    f"📌 Задача {task['id']}:\n{task['question']}",
                    reply_markup=markup
                )

                user_state[user_id]["mode"] = "solving_task"
                user_state[user_id]["topic"] = topic
                user_state[user_id]["task_id"] = task_id
            return


        elif text == "🚫 Отметить как не решённую":
            topic = user_state[user_id].get("topic")
            task_id = str(user_state[user_id].get("task_id"))

        # ✅ Отмечаем как не решённую
            if topic not in users_data[str(user_id)]:
                users_data[str(user_id)][topic] = {}
            users_data[str(user_id)][topic][task_id] = "failed"
            save_users(users_data)

            # Показываем список задач снова
            task_data = load_tasks().get(topic, {})
            task_buttons = [[f"№ {t['id']}"] for t in task_data.get("tasks", [])]
            task_buttons.append(["⬅️ Назад"])
            markup = ReplyKeyboardMarkup(task_buttons, resize_keyboard=True)

            await update.message.reply_text(
                f"📚 Тема: *{topic}*\nЗадача не решена. Выбери другую задачу:",
                reply_markup=markup,
                parse_mode="Markdown"
            )
            user_state[user_id]["mode"] = "choosing_task"
            return

        

    # Выбор класса
    if text == "🎯 Подготовка к поступлению в 7 класс":
        user_state[user_id] = {"prev_menu": "start"}
        menu_buttons = [
            ["📂 Задачи по темам", "🧪 Полные тесты"],
            ["📊 Проверить прогресс", "🧠 Что решать дальше?"],
            ["🔥 Задача дня", "ℹ️ Информация об экзамене"],
            ["⬅️ Назад"]
        ]
        markup = ReplyKeyboardMarkup(menu_buttons, resize_keyboard=True)
        await update.message.reply_text("Выбери, с чего начнём:", reply_markup=markup)
    #Профиль Прогресс
    elif text == "📊 Проверить прогресс":
        profile = users_data.get(str(user_id), {})
        full_name = profile.get("full_name", "Имя не указано")
        school = profile.get("school", "Школа не указана")

        msg = f"👤 *Профиль*\n\n"
        msg += f"*ФИО:* {full_name}\n"
        msg += f"*Школа:* {school}\n\n"
        # Задача дня — Streak
        streak = profile.get("streak", {})
        current_streak = streak.get("current", 0)

        if current_streak > 0:
            bars = "🔥" * min(current_streak, 10)
            msg += f"*🔥 Задача дня:*\nТы решал {current_streak} дней подряд!\n{bars}\n\n"
        msg += "📂 *Задачи по темам:*\n"
        
        # Прогресс по темам
        tasks = load_tasks()
        for topic, topic_data in tasks.items():
            user_topic_data = profile.get(topic, {})
            total = len(topic_data["tasks"])
            solved = sum(1 for v in user_topic_data.values() if v == "solved")
            failed = sum(1 for v in user_topic_data.values() if v == "failed")
            untouched = total - solved - failed

            green = solved * 10 // total
            red = failed * 10 // total
            white = 10 - green - red
            if solved > 0 and green == 0:
                green = 1
                white = max(white - 1, 0)
            # Смайлики: 🟩⬜🟥
            bars = "🟩" * green
            bars += "⬜" * white
            bars += "🟥" * red
           
            msg += f"*{topic}* — решено {solved}/{total}, ошибок {failed}\n{bars}\n\n"

        # Прогресс по тестам
        tests_data = load_tests()
        msg += "*🧪 Пройденные тесты:*\n"
        for test in tests_data["tests"]:
            test_id = str(test["id"])
            if test_id in profile.get("tests", {}):
                score = profile["tests"][test_id]["score"]
                bars = "🟩" * (score * 10 // 150)
                bars += "🟥" * (10 - len(bars))
                msg += f"{test['title']} — {score}/150\n{bars}\n\n"

        # Кнопки
        buttons = [["⬅️ Назад", "✏️ Изменить профиль"]]
        markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        user_state[user_id] = {
            "prev_menu": "main_menu",
            "mode": None
        }

        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=markup)

    
    elif text == "✏️ Изменить профиль":
        user_state[user_id]["mode"] = "editing_profile_menu"
        buttons = [
            ["📝 Изменить ФИО", "🏫 Изменить школу"],
            ["⬅️ Назад"]
        ]
        markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        await update.message.reply_text("Что ты хочешь изменить?", reply_markup=markup)

    elif text == "📝 Изменить ФИО":
        user_state[user_id]["mode"] = "editing_full_name"
        await update.message.reply_text("✏️ Введи своё ФИО (например: *Ткаченко Влад*)", parse_mode="Markdown")

    elif user_state.get(user_id, {}).get("mode") == "editing_full_name":
        users_data[str(user_id)]["full_name"] = text.strip()
        save_users(users_data)
        user_state[user_id]["mode"] = None
        await update.message.reply_text("✅ ФИО обновлено.")
    elif text == "🏫 Изменить школу":
        user_state[user_id]["mode"] = "editing_school"
        await update.message.reply_text("🏫 Введи название своей школы: (например: РФМШ)")

    elif user_state.get(user_id, {}).get("mode") == "editing_school":
        users_data[str(user_id)]["school"] = text.strip()
        save_users(users_data)
        user_state[user_id]["mode"] = None
        await update.message.reply_text("✅ Школа обновлена.")
    

    # Задачи по темам
    elif text == "📂 Задачи по темам":
        tasks = load_tasks()
        topic_buttons = [[topic.capitalize()] for topic in tasks.keys()]
        topic_buttons.append(["⬅️ Назад"])
        markup = ReplyKeyboardMarkup(topic_buttons, resize_keyboard=True)
        await update.message.reply_text("Выбери тему:", reply_markup=markup)

        user_state[user_id] = {
            "mode": "choosing_topic",
            "prev_menu": "main_menu"
        }


    # Инфо об экзамене
    elif text == "ℹ️ Информация об экзамене":
        user_state[user_id]["prev_menu"] = "start"
        await update.message.reply_text(
            "📘 *Информация о вступительном экзамене в РФМШ*\n\n"
            "*Формат экзамена:*\n"
            "— Предметы: *математика* и *логика*\n"
            "— Время: *120 минут*\n"
            "— Все задачи — *открытого типа* (нужно вписать целое число)\n"
            "— Разное количество баллов за задачи разной сложности:\n"
            "  • 10 задач по *3 балла*\n"
            "  • 10 задач по *5 баллов*\n"
            "  • 10 задач по *7 баллов*\n\n"
            "*Максимальный балл:* 150\n"
            "❗ Неверный ответ или его отсутствие — *0 баллов*\n\n"
            "📅 *Важные даты:*\n"
            "— 15 января 2025 — старт регистрации (до 3 апреля)\n"
            "— 27 апреля 2025 — *экзамен для 7 класса*\n\n"
            "📍 *Города проведения:*\n"
            "Астана, Алматы, Атырау, Актау, Орал, Туркестан, Шымкент",
            parse_mode="Markdown"
        )

        # Проверка выбора темы
    elif user_state.get(user_id, {}).get("mode") == "choosing_topic":
        tasks = load_tasks()
        matched_topic = None
        for topic in tasks:
            if topic.lower() == text.lower():
                matched_topic = topic
                break

        if matched_topic:
            user_state[user_id] = {
                "mode": "choosing_task",
                "topic": matched_topic,
                "prev_menu": "topics"
            }

            # ✅ Добавление галочек/крестиков
            user_tasks = users_data.get(str(user_id), {}).get(matched_topic, {})
            task_buttons = []

            for t in tasks[matched_topic]["tasks"]:
                task_id_str = str(t["id"])
                mark = "❓"
                if isinstance(user_tasks, dict):
                    if task_id_str in user_tasks and user_tasks[task_id_str] == "solved":
                        mark = "✅"
                    elif task_id_str in user_tasks and user_tasks[task_id_str] == "failed":
                        mark = "❌"
                task_buttons.append([f"{mark} № {t['id']}"])

            task_buttons.append(["⬅️ Назад"])
            markup = ReplyKeyboardMarkup(task_buttons, resize_keyboard=True)

            await update.message.reply_text(
                f"📚 Тема: *{matched_topic}*\nВыбери номер задачи:",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("Такой темы нет. Выбери из списка кнопок.")
    # Выбор задачи
    elif user_state.get(user_id, {}).get("mode") == "choosing_task":
        topic = user_state[user_id]["topic"]
        task_id_text = text.replace("№", "").strip()
        task_id_text = task_id_text.replace("✅", "").replace("❌", "").replace("❓", "").strip()  # <-- фикс

        if task_id_text.isdigit():
            task_id = int(task_id_text)
            topic_data = load_tasks().get(topic, {})
            task = next((t for t in topic_data.get("tasks", []) if t["id"] == task_id), None)

            if task:
                buttons = [
                    ["🧠 Объяснение темы", "🧮 Объяснение решения"],
                    ["✅ Отправить ответ"],
                    ["⬅️ Назад"]
                ]
                markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

                await update.message.reply_text(
                    f"📌 Задача {task['id']}:\n{task['question']}",
                    reply_markup=markup
                )

                user_state[user_id]["mode"] = "solving_task"
                user_state[user_id]["task_id"] = task_id
                return

    elif text == "🧪 Полные тесты":
        tests_data = load_tests()
        user_tests = users_data.get(str(user_id), {}).get("tests", {})

        buttons = []
        for test in tests_data["tests"]:
            test_id = str(test["id"])
            score = user_tests.get(test_id, {}).get("score")
            title = test["title"]

            if score is not None:
                title += f" ({score}/150)"

            buttons.append([title])
        buttons.append(["⬅️ Назад"])

        markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

        user_state[user_id] = {
            "mode": "choosing_full_test",
            "prev_menu": "main_menu"
        }

        await update.message.reply_text("📚 Выбери тест и подожди 10 секунд для отправки файла", reply_markup=markup)

    elif user_state.get(user_id, {}).get("mode") == "choosing_full_test":
        tests_data = load_tests()
        clean_text = text.split(" (")[0]
        selected_test = next((test for test in tests_data["tests"] if test["title"] == clean_text), None)

        if selected_test:
            file_path = f"data/tests/{selected_test['file']}"
            try:
                with open(file_path, "rb") as f:
                    await update.message.reply_document(
                        document=f,
                        filename=selected_test["file"],
                        caption=f"🧪 *{selected_test['title']}*",
                        parse_mode="Markdown"
                    )
            except FileNotFoundError:
                await update.message.reply_text("❌ Файл не найден. Пожалуйста, обратись в поддержку.")
                return

            user_state[user_id] = {
                "mode": "awaiting_test_answers",
                "test_id": selected_test["id"],
                "prev_menu": "main_menu"
            }

            markup = ReplyKeyboardMarkup([
                ["✅ Отправить ответы"],
                ["⬅️ Назад"]
            ], resize_keyboard=True)
            await update.message.reply_text("📥 Готово. Теперь нажми кнопку ниже, чтобы ввести ответы 👇", reply_markup=markup)


    elif text == "✅ Отправить ответы" and user_state.get(user_id, {}).get("mode") == "awaiting_test_answers":
        await update.message.reply_text("✏️ Введи все 30 ответов через пробел \n (например - 14 28 1/3 ...)")
        user_state[user_id]["mode"] = "awaiting_test_input"
        return

    elif user_state.get(user_id, {}).get("mode") == "awaiting_test_input":
        try:
            answers = text.strip().upper().split()
            if len(answers) != 30:
                await update.message.reply_text("❗ Ответов должно быть *ровно 30*. Попробуй снова.", parse_mode="Markdown")
                return

            tests_data = load_tests()
            current_test_id = user_state[user_id]["test_id"]
            current_test = next((t for t in tests_data["tests"] if t["id"] == current_test_id), None)

            if not current_test:
                await update.message.reply_text("⚠️ Ошибка: тест не найден.")
                return

            correct = current_test["answers"]
            result = []
            correct_count = 0
            total_score = 0

            for i in range(30):
                if answers[i].strip().upper() == correct[i].strip().upper():
                    correct_count += 1
                    if i < 10:
                        total_score += 3
                    elif i < 20:
                        total_score += 5
                    else:
                        total_score += 7
                    result.append(f"{i+1}. ✅")
                else:
                    result.append(f"{i+1}. ❌ (тв: {answers[i]} / верн: {correct[i]})")

            await update.message.reply_text(
                f"🎯 Правильных ответов: {correct_count}/30\n"
                f"💯 Твой балл: {total_score} из 150\n\n"
                + "\n".join(result)
            )

            # Сохраняем в users.json
            if "tests" not in users_data[str(user_id)]:
                users_data[str(user_id)]["tests"] = {}

            users_data[str(user_id)]["tests"][str(current_test_id)] = {
                "score": total_score,
                "correct": correct_count
            }
            save_users(users_data)

            user_state[user_id]["mode"] = "test_result"

            markup = ReplyKeyboardMarkup(
                [["📌 Отметить как правильные"], ["⬅️ Назад"]],
                resize_keyboard=True
            )
            await update.message.reply_text("📋 Выбери, что дальше:", reply_markup=markup)

        except Exception as e:
            print("[ERROR in test input]", e)
            await update.message.reply_text("❌ Произошла ошибка при проверке ответов. Попробуй ещё раз.")

    elif text == "📌 Отметить как правильные" and user_state.get(user_id, {}).get("mode") == "test_result":
        await update.message.reply_text("✏️ Введи номера задач, которые ты решил правильно , но бот их не засчитал (например: `2 4 15`):", parse_mode="Markdown")
        user_state[user_id]["mode"] = "mark_test_correction"
        return

    elif user_state.get(user_id, {}).get("mode") == "mark_test_correction":
        try:
            indexes = list(map(int, text.strip().split()))
            current_test_id = user_state[user_id]["test_id"]
            tests_data = load_tests()
            current_test = next((t for t in tests_data["tests"] if t["id"] == current_test_id), None)

            if not current_test:
                await update.message.reply_text("⚠️ Ошибка при поиске теста.")
                return

            # Пересчитываем баллы
            corrected = users_data[str(user_id)]["tests"][str(current_test_id)]
            already_correct = corrected["correct"]
            new_correct = 0
            added_score = 0

            for i in indexes:
                if i < 1 or i > 30:
                    continue
                if i <= 10:
                    added_score += 3
                elif i <= 20:
                    added_score += 5
                else:
                    added_score += 7
                new_correct += 1

            corrected["score"] += added_score
            corrected["correct"] += new_correct
            save_users(users_data)

            user_state[user_id]["mode"] = "test_result"
            await update.message.reply_text(
                f"✅ Обновлено!\n🎯 Правильных ответов: {corrected['correct']}/30\n💯 Балл: {corrected['score']} из 150",
                reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True)
            )

        except Exception as e:
            print("[ERROR in correction]", e)
            await update.message.reply_text("❌ Ошибка при обработке. Введи номера задач через пробел.")

    elif text == "🧠 Что решать дальше?":
        from datetime import datetime
        tasks = load_tasks()
        profile = users_data.get(str(user_id), {})

        topic_scores = {}

        for topic, data in tasks.items():
            user_topic = profile.get(topic, {})
            solved = sum(1 for v in user_topic.values() if v == "solved")
            failed = sum(1 for v in user_topic.values() if v == "failed")
            total = len(data["tasks"])
            progress = (solved + failed) / total if total else 0

            score = 0
            if failed > 0:
                score += 2
            if progress < 0.5:
                score += 1
            score += data.get("weight", 1.0)

            topic_scores[topic] = score

        scores = sorted(topic_scores.items(), key=lambda x: -x[1])

        # Подсчёт решённых задач и тем
        total_tasks_done = 0
        unique_topics_solved = set()
        for topic_name, topic_data in tasks.items():
            user_topic = profile.get(topic_name, {})
            for task in topic_data["tasks"]:
                if user_topic.get(str(task["id"])) == "solved":
                    total_tasks_done += 1
                    unique_topics_solved.add(topic_name)

        tests_done = len(profile.get("tests", {}))

        encouraging = ""
        if total_tasks_done >= 25:
            encouraging = f"Ты решил уже *{total_tasks_done} задач* по *{len(unique_topics_solved)} темам* – 🔥 ты большой молодец!"
        elif total_tasks_done >= 10:
            encouraging = f"Уже *{total_tasks_done} задач* по *{len(unique_topics_solved)} темам* за плечами – крутое начало! 💪"
        else:
            encouraging = f"Ты пока решил *{total_tasks_done} задач* – и это только старт. Дальше будет только круче! 🙌"

        top_topic, top_score = scores[0]
        failed = sum(1 for v in profile.get(top_topic, {}).values() if v == "failed")
        progress = len(profile.get(top_topic, {})) / len(tasks[top_topic]["tasks"])

        if failed > 0:
            reason = f"В этой теме у тебя были ошибки – важно закрыть пробелы перед экзаменом."
        elif progress < 0.3:
            reason = f"Ты почти не решал задачи по этой теме – пора восполнить!"
        else:
            reason = f"Ты уже немного решал эту тему – продолжай, чтобы закрепить уверенность 💡"

        test_hint = ""
        if tests_done == 0:
            test_hint = "\n\n🧪 *Рекомендация:* Начни с полного теста — он поможет понять структуру экзамена."
        elif tests_done >= 3:
            test_hint = "\n\n📘 *Совет:* Все пробники пройдены. Советую докупить оф. варианты на сайте РФМШ!"

        await update.message.reply_text(
            f"{encouraging}\n\n"
            f"🎯 *Рекомендуемая тема:*\n👉 *{top_topic}*\n\n"
            f"📌 Почему: {reason}{test_hint}",
            parse_mode="Markdown"
        )
    elif text == "🔥 Задача дня":
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")

        if "daily_task" not in user_state or user_state["daily_task"].get("date") != today:
            tasks = load_tasks()
            all_tasks = []
            for topic, data in tasks.items():
                for task in data["tasks"]:
                    all_tasks.append({
                        "topic": topic,
                        "id": task["id"],
                        "question": task["question"],
                        "answer": task["answer"],
                        "explanation": task["explanation"]
                    })
            chosen = random.choice(all_tasks)
            user_state["daily_task"] = {
                "date": today,
                "task": chosen,
                "answered": False
            }

        chosen = user_state["daily_task"]["task"]
        user_state[user_id] = {
            "mode": "daily_solving",
            "prev_menu": "main_menu",
            "daily_task": chosen
        }

        buttons = [
            ["🧠 Объяснение темы", "🧮 Объяснение решения"],
            ["✅ Отправить ответ"],
            ["⬅️ Назад"]
        ]
        markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

        await update.message.reply_text(
            f"📅 *Задача дня*\n\n"
            f"Каждый день ты получаешь одну уникальную задачу. Реши её, чтобы прокачать streak и попасть в список лучших! 🔥\n\n"
            f"*Тема:* {chosen['topic']}\n\n📌 {chosen['question']}",
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif user_state.get(user_id, {}).get("mode") == "daily_solving":
        if text == "✅ Отправить ответ":
            await update.message.reply_text("✏️ Введи свой ответ:")
            user_state[user_id]["mode"] = "daily_waiting"
            return
        elif text == "🧠 Объяснение темы":
            topic = user_state[user_id]["daily_task"]["topic"]
            explanation = load_tasks().get(topic, {}).get("explanation")
            await update.message.reply_text(f"🧠 Объяснение по теме *{topic}*:\n{explanation or 'Пока нет данных.'}", parse_mode="Markdown")
            return
        elif text == "🧮 Объяснение решения":
            explanation = user_state[user_id]["daily_task"]["explanation"]
            await update.message.reply_text(f"🧮 Объяснение:\n{explanation}")
            return

    elif user_state.get(user_id, {}).get("mode") == "daily_waiting":
        task = user_state[user_id]["daily_task"]
        topic = task["topic"]
        task_id = str(task["id"])

        if text == "✅ Отправить ответ":
            await update.message.reply_text("✏️ Введи свой ответ:")
            return
        elif text == "🧠 Объяснение темы":
            explanation = load_tasks().get(topic, {}).get("explanation")
            await update.message.reply_text(f"🧠 Объяснение по теме *{topic}*:\n{explanation or 'Пока нет данных.'}", parse_mode="Markdown")
            return
        elif text == "🧮 Объяснение решения":
            await update.message.reply_text(f"🧮 Объяснение:\n{task['explanation']}")
            return
        elif text == "⬅️ Назад":
            markup = ReplyKeyboardMarkup([
                ["📂 Задачи по темам", "🧪 Полные тесты"],
                ["📊 Проверить прогресс", "🧠 Что решать дальше?"],
                ["🔥 Задача дня", "ℹ️ Информация об экзамене"],
                ["⬅️ Назад"]
            ], resize_keyboard=True)
            await update.message.reply_text("⬅️ Возврат в меню", reply_markup=markup)
            user_state[user_id] = {"mode": None, "prev_menu": "start"}
            return

        if text.strip().lower() == task["answer"].strip().lower():
            await update.message.reply_text("✅ Правильно! Отличная работа 💪")
            from datetime import datetime, timedelta
            today = datetime.now().strftime("%Y-%m-%d")
            profile = users_data.get(str(user_id), {})
            streak_data = profile.get("streak", {})

            if streak_data.get("last_solved") != today:
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                streak = streak_data.get("current", 0) + 1 if streak_data.get("last_solved") == yesterday else 1
                profile["streak"] = {"current": streak, "last_solved": today}
                users_data[str(user_id)] = profile

            if topic not in users_data[str(user_id)]:
                users_data[str(user_id)][topic] = {}
            users_data[str(user_id)][topic][task_id] = "solved"
            save_users(users_data)

            buttons = [
                ["🧠 Объяснение темы", "🧮 Объяснение решения"],
                ["⬅️ Назад"]
            ]
            markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
            await update.message.reply_text("🧠 Хочешь разобраться глубже? Выбери, что дальше:", reply_markup=markup)
            user_state[user_id]["mode"] = "daily_after_correct"
        else:
            markup = ReplyKeyboardMarkup([
                ["🔁 Попробовать снова", "🧮 Объяснение решения"],
                ["⬅️ Назад"]
            ], resize_keyboard=True)
            await update.message.reply_text("❌ Неправильно. Попробуй ещё раз или посмотри решение.", reply_markup=markup)
            user_state[user_id]["mode"] = "daily_wrong"
        return

    elif user_state.get(user_id, {}).get("mode") == "daily_wrong":
        task = user_state[user_id]["daily_task"]
        if text == "🔁 Попробовать снова":
            user_state[user_id]["mode"] = "daily_solving"
            buttons = [
                ["🧠 Объяснение темы", "🧮 Объяснение решения"],
                ["✅ Отправить ответ"],
                ["⬅️ Назад"]
            ]
            markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
            await update.message.reply_text(f"📌 Задача дня:\n{task['question']}", reply_markup=markup)
            return
        elif text == "🧮 Объяснение решения":
            await update.message.reply_text(f"🧮 Объяснение:\n{task['explanation']}")
            return

    elif user_state.get(user_id, {}).get("mode") == "daily_after_correct":
        if text == "🧠 Объяснение темы":
            topic = user_state[user_id]["daily_task"]["topic"]
            explanation = load_tasks().get(topic, {}).get("explanation")
            await update.message.reply_text(f"🧠 Объяснение по теме *{topic}*:\n{explanation or 'Нет данных.'}", parse_mode="Markdown")
            return
        elif text == "🧮 Объяснение решения":
            await update.message.reply_text(f"🧮 Объяснение:\n{user_state[user_id]['daily_task']['explanation']}")
            return
       

# Обработка выбора темы 
async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    # Проверяем, ждет ли бот выбор темы
    if user_state.get(user_id, {}).get("mode") != "choosing_topic":
        return

    tasks = load_tasks()
    matched_topic = None

    for topic in tasks:
        if topic.lower() == text.lower():
            matched_topic = topic
            break

    if matched_topic:
        user_state[user_id] = {
            "mode": "choosing_task",
            "topic": matched_topic,
            "prev_menu": "topics"
        }

        task_buttons = [[f"№ {task['id']}"] for task in tasks[matched_topic]["tasks"]]
        task_buttons.append(["⬅️ Назад"])
        markup = ReplyKeyboardMarkup(task_buttons, resize_keyboard=True)

        await update.message.reply_text(
            f"📚 Тема: *{matched_topic}*\nВыбери номер задачи:",
            reply_markup=markup,
            parse_mode="Markdown"
        )

# Запуск бота

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    app.run_polling()

if __name__ == "__main__":
    main()
