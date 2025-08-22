import os
from telebot import TeleBot, types
from dotenv import load_dotenv
from db.user_info_db import User_info
from keyboards import *
from datetime import datetime
import random
import json
import time
import threading

load_dotenv()

# ====== Bot sozlamalari ======
token = os.getenv('TOKEN')
bot = TeleBot(token)
ADMIN_ID = os.getenv("ADMIN_ID")  # e'tibor: matn sifatida saqlanadi
group_username = '@codecraftdevelop'
db = User_info()

# WebApp URL manzillari
chess_webapp_url = "https://whitewolf031.github.io/game_bot/web_app/chess.html"
shashka_webapp_url = "https://whitewolf031.github.io/game_bot/web_app/shashka.html"


# WebApp-ga havola yaratish funksiyasi
def create_webapp_button(game_id, player_id, game_type):
    if game_type == "chess":
        url = f"{chess_webapp_url}?game_id={game_id}&player_id={player_id}"
    else:
        url = f"{shashka_webapp_url}?game_id={game_id}&player_id={player_id}"

    return types.InlineKeyboardButton(
        text="🎮 O'yinni boshlash" if game_type == "chess" else "🔴⚪ O'yinni boshlash",
        web_app=types.WebAppInfo(url=url)
    )


# ====== Chess game states ======
chess_games = {}
active_players = {}

# ====== Shashka game states ======
shashka_games = {}
shashka_active_players = {}

# ====== TEST (2 foydalanuvchi o‘zaro bellashadi) ======
TEST_TIME_LIMIT = 30.0           # Har bir savol uchun 30 soniya
AFTER_EXPLANATION_DELAY = 2.0    # Keyingi savolga o'tishdan oldin 2 soniya kutish (bloklamasdan)

test_questions = []              # Savollar banki
test_waiting_users = []          # Juftlik kutayotganlar navbati
active_tests = {}                # test_id -> test holati
test_timers = {}                 # test_id -> threading.Timer obyekti


# --- Test savollarini fayldan yuklash/saqlash ---
def load_test_questions():
    global test_questions
    try:
        with open('test_questions.json', 'r', encoding='utf-8') as f:
            test_questions = json.load(f)
    except FileNotFoundError:
        test_questions = [
            {
                "question": "x = 7 + 3 * 2 ifodaning qiymati nechiga teng?",
                "options": ["20", "13", "17"],
                "correct_answer": 1,
                "explanation": "✅ Javob: B (3*2=6, 7+6=13)"
            },
            {
                "question": "Python qaysi dasturlash tiliga kiradi?",
                "options": ["Compiled", "Interpreted", "Machine"],
                "correct_answer": 1,
                "explanation": "✅ Javob: B (Python interpreted til)"
            },
            {
                "question": "Quyidagilardan qaysi biri ma'lumotlar strukturasi emas?",
                "options": ["Array", "Function", "Linked List"],
                "correct_answer": 1,
                "explanation": "✅ Javob: B (Function — ma'lumotlar strukturasi emas)"
            }
        ]
        save_test_questions()


def save_test_questions():
    with open('test_questions.json', 'w', encoding='utf-8') as f:
        json.dump(test_questions, f, ensure_ascii=False, indent=4)


# --- TEST boshqaruvi ---
@bot.message_handler(func=lambda msg: msg.text == "Test yechish")
def start_test(message):
    """
    Foydalanuvchini juftlik navbatiga qo‘shadi va 2 kishi to‘lganda testni boshlaydi.
    Har savol uchun 30s taymer ishlaydi. Faqat tugma bosilganida yoki vaqt tugaganda keyingi savolga o'tadi.
    """
    chat_id = message.chat.id

    if not test_questions:
        bot.send_message(chat_id, "📂 Hozircha test savollari mavjud emas.")
        return

    if chat_id in test_waiting_users:
        bot.send_message(chat_id, "⏳ Siz allaqachon juftlik navbatidasiz. Iltimos, biroz kuting.")
        return

    test_waiting_users.append(chat_id)
    bot.send_message(chat_id, "⏳ Juftlik kutyapsiz. Boshqa foydalanuvchi qo'shilishini kuting.")

    # 2 ta foydalanuvchi to‘planganda testni boshlaymiz
    if len(test_waiting_users) >= 2:
        user1_id = test_waiting_users.pop(0)
        user2_id = test_waiting_users.pop(0)

        # Savollar tartibi (shuffle)
        question_order = list(range(len(test_questions)))
        random.shuffle(question_order)

        test_id = f"test_{user1_id}_{user2_id}_{int(time.time())}"
        active_tests[test_id] = {
            "players": [user1_id, user2_id],
            "scores": {user1_id: 0, user2_id: 0},
            "current_question": 0,                          # index in order
            "answers": {user1_id: None, user2_id: None},
            "start_time": time.time(),
            "question_start_time": None,
            "order": question_order,                        # savollar ketma-ketligi
        }

        # Har ikkala o‘yinchiga test boshlandi deb yozamiz
        for uid in (user1_id, user2_id):
            try:
                bot.send_message(uid, "🧠 Test boshlandi! Har bir savolga javob berish uchun 30 soniya vaqt beriladi.")
            except Exception as e:
                print(f"Start test notice error (uid={uid}): {e}")

        send_test_question(test_id)


def send_test_question(test_id):
    """Joriy savolni har ikki o‘yinchiga yuboradi va 30s taymerni ishga tushiradi."""
    if test_id not in active_tests:
        return

    test = active_tests[test_id]
    order = test["order"]
    q_idx = test["current_question"]

    # Test tugash sharti
    if q_idx >= len(order):
        finish_test(test_id)
        return

    question_data = test_questions[order[q_idx]]
    test["question_start_time"] = time.time()

    # Varianti tugmalari
    markup = types.InlineKeyboardMarkup()
    label_map = ['A', 'B', 'C', 'D', 'E']
    options = question_data.get("options", [])[:5]
    for i, option_text in enumerate(options):
        markup.add(
            types.InlineKeyboardButton(
                f"{label_map[i]}) {option_text}",
                callback_data=f"test_answer_{test_id}_{i}"
            )
        )

    # Savol matni
    text = (
        f"Savol {q_idx + 1}/{len(order)}:\n"
        f"{question_data.get('question', 'Savol topilmadi')}\n\n"
        f"⏳ Javob berish uchun {int(TEST_TIME_LIMIT)} soniya vaqtingiz bor!"
    )

    # Har bir o'yinchi uchun savol yuborish
    for uid in test["players"]:
        try:
            bot.send_message(uid, text, reply_markup=markup)
        except Exception as e:
            print(f"Savol yuborishda xatolik (uid={uid}): {e}")

    # Yangi taymer
    start_test_timer(test_id)


def start_test_timer(test_id):
    """30 soniyalik taymerni ishga tushiradi. Avvalgi taymer bo‘lsa bekor qiladi."""
    # Eski taymer bo‘lsa o‘chirib tashlaymiz
    old = test_timers.get(test_id)
    if old:
        try:
            old.cancel()
        except Exception:
            pass

    timer = threading.Timer(TEST_TIME_LIMIT, handle_timeout, args=[test_id])
    test_timers[test_id] = timer
    timer.start()


def handle_timeout(test_id):
    """Vaqt tugaganda javob bermaganlarga xabar yuboradi va javoblarni tekshiradi."""
    if test_id not in active_tests:
        return

    test = active_tests[test_id]
    unanswered = [uid for uid, ans in test["answers"].items() if ans is None]

    if unanswered:
        for uid in unanswered:
            try:
                bot.send_message(uid, "⏰ Vaqt tugadi! Siz javob bermadingiz.")
            except Exception as e:
                print(f"Timeout xabarida xatolik (uid={uid}): {e}")

        # Taymer obyektini tozalaymiz
        t = test_timers.get(test_id)
        if t:
            try:
                t.cancel()
            except Exception:
                pass
            finally:
                test_timers.pop(test_id, None)

        # Javoblarni tekshiraman (kimdir javob bergan bo‘lishi mumkin)
        check_test_answers(test_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('test_answer_'))
def handle_test_answer(call):
    """Foydalanuvchi javobini qabul qilish; ikkala kishi javob berganda tekshiradi."""
    user_id = call.from_user.id
    try:
        _, _, test_id, idx_str = call.data.split('_', 3)
        answer_index = int(idx_str)
    except Exception:
        bot.answer_callback_query(call.id, "❌ Xato format.")
        return

    if test_id not in active_tests:
        bot.answer_callback_query(call.id, "Bu test allaqachon tugagan.")
        return

    test = active_tests[test_id]
    if user_id not in test["players"]:
        bot.answer_callback_query(call.id, "Siz bu testda ishtirok etmaysiz.")
        return

    # Allaqachon javob berganmi?
    if test["answers"][user_id] is not None:
        bot.answer_callback_query(call.id, "Siz allaqachon javob berdingiz!")
        return

    # Javobni saqlaymiz
    test["answers"][user_id] = answer_index
    bot.answer_callback_query(call.id, "Javobingiz qabul qilindi!")

    # Agar ikkala foydalanuvchi ham javob bergan bo'lsa – taymerni bekor qilib, tekshiramiz
    if all(ans is not None for ans in test["answers"].values()):
        t = test_timers.get(test_id)
        if t:
            try:
                t.cancel()
            except Exception:
                pass
            finally:
                test_timers.pop(test_id, None)
        check_test_answers(test_id)


def check_test_answers(test_id):
    """Joriy savol bo‘yicha to‘g‘ri javobni e’lon qiladi, ballarni yangilaydi va keyingi savolni rejalashtiradi."""
    if test_id not in active_tests:
        return

    test = active_tests[test_id]
    order = test["order"]
    q_idx = test["current_question"]

    # Tugash tekshiruvi
    if q_idx >= len(order):
        finish_test(test_id)
        return

    # Joriy savol
    question_data = test_questions[order[q_idx]]
    correct_answer = int(question_data["correct_answer"])  # indeks

    # Ballarni hisoblash
    for uid, ans in test["answers"].items():
        if ans == correct_answer:
            test["scores"][uid] += 1

    # To'g'ri javob va tushuntirishni yuborish
    label_map = ['A', 'B', 'C', 'D', 'E']
    correct_label = label_map[correct_answer] if 0 <= correct_answer < len(label_map) else "?"
    explanation = question_data.get('explanation', '')
    for uid in test["players"]:
        try:
            bot.send_message(uid, f"✅ To'g'ri javob: {correct_label}\n{explanation}")
        except Exception as e:
            print(f"Javob yuborishda xatolik (uid={uid}): {e}")

    # Keyingi savolga tayyorgarlik
    test["current_question"] += 1
    test["answers"] = {uid: None for uid in test["players"]}

    # 2 soniyadan keyin keyingi savolni yuboramiz (bloklamasdan)
    threading.Timer(AFTER_EXPLANATION_DELAY, send_test_question, args=[test_id]).start()


def finish_test(test_id):
    """Test yakuni: g‘olibni aniqlash, ball berish/ayirish, xabar yuborish va tozalash."""
    if test_id not in active_tests:
        return

    test = active_tests[test_id]
    user1_id, user2_id = test["players"]
    score1 = test["scores"][user1_id]
    score2 = test["scores"][user2_id]

    # Taymer bo‘lsa o‘chirib tashlaymiz
    t = test_timers.get(test_id)
    if t:
        try:
            t.cancel()
        except Exception:
            pass
        finally:
            test_timers.pop(test_id, None)

    # Ballarni yangilash (g‘olibga +10, yutqazganga -10)
    if score1 > score2:
        try:
            db.add_points_to_user(user1_id, 10)
            db.add_points_to_user(user2_id, -10)
        except Exception as e:
            print(f"DB points error: {e}")
    elif score2 > score1:
        try:
            db.add_points_to_user(user1_id, -10)
            db.add_points_to_user(user2_id, 10)
        except Exception as e:
            print(f"DB points error: {e}")

    # Natija matnlari
    if score1 > score2:
        result_text1 = f"🎉 Tabriklaymiz! Siz yutdingiz!\nSiz: {score1} ball\nRaqibingiz: {score2} ball\n+10 ball"
        result_text2 = f"😞 Siz yutqazdingiz.\nSiz: {score2} ball\nRaqibingiz: {score1} ball\n-10 ball"
    elif score2 > score1:
        result_text1 = f"😞 Siz yutqazdingiz.\nSiz: {score1} ball\nRaqibingiz: {score2} ball\n-10 ball"
        result_text2 = f"🎉 Tabriklaymiz! Siz yutdingiz!\nSiz: {score2} ball\nRaqibingiz: {score1} ball\n+10 ball"
    else:
        result_text1 = f"🤝 Durrang!\nSiz: {score1} ball\nRaqibingiz: {score2} ball\nHech qanday o'zgarishsiz"
        result_text2 = result_text1

    # Natijalarni yuborish
    try:
        bot.send_message(user1_id, result_text1)
        bot.send_message(user2_id, result_text2)
    except Exception as e:
        print(f"Natija yuborishda xatolik: {e}")

    # Tozalash
    active_tests.pop(test_id, None)


# --- Admin uchun test savollarini boshqarish ---
@bot.message_handler(func=lambda msg: msg.text == "Test savollari" and str(msg.from_user.id) == str(ADMIN_ID))
def manage_test_questions(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Savol qoʻshish", "📋 Savollar roʻyxati")
    markup.add("🔙 Bosh menyu")

    bot.send_message(message.chat.id, "Test savollarini boshqarish:", reply_markup=markup)
    bot.register_next_step_handler(message, process_test_management)


def process_test_management(message):
    if message.text == "➕ Savol qoʻshish":
        msg = bot.send_message(message.chat.id, "Yangi savolni kiriting:")
        bot.register_next_step_handler(msg, process_new_question)
    elif message.text == "📋 Savollar roʻyxati":
        list_test_questions(message)
    elif message.text == "🔙 Bosh menyu":
        bot.send_message(message.chat.id, "Bosh menyu:", reply_markup=menu_keyboards())
        bot.register_next_step_handler(message, main_menu)


def process_new_question(message):
    question = message.text
    msg = bot.send_message(
        message.chat.id,
        "Endi variantlarni kiriting (har biri yangi qatorda, format: A) variant1):"
    )
    bot.register_next_step_handler(msg, process_options, question)


def process_options(message, question):
    options_text = message.text
    options = []
    correct_answer = None

    lines = options_text.split('\n')
    for i, line in enumerate(lines):
        if line.strip():
            parts = line.split(')', 1)
            if len(parts) > 1:
                options.append(parts[1].strip())
                if correct_answer is None:
                    correct_answer = i

    if len(options) < 2:
        bot.send_message(message.chat.id, "❗ Kamida 2 ta variant kiriting!")
        return

    msg = bot.send_message(message.chat.id, "Tushuntirishni kiriting (to'g'ri javob haqida):")
    bot.register_next_step_handler(msg, process_explanation, question, options, correct_answer)


def process_explanation(message, question, options, correct_answer):
    explanation = message.text

    new_question = {
        "question": question,
        "options": options,
        "correct_answer": int(correct_answer) if correct_answer is not None else 0,
        "explanation": explanation
    }

    test_questions.append(new_question)
    save_test_questions()

    bot.send_message(message.chat.id, "✅ Savol muvaffaqiyatli qo'shildi!", reply_markup=menu_keyboards())
    bot.register_next_step_handler(message, main_menu)


def list_test_questions(message):
    if not test_questions:
        bot.send_message(message.chat.id, "Hozircha hech qanday savol mavjud emas.")
        return

    questions_text = "📋 Test savollari ro'yxati:\n\n"
    for i, q in enumerate(test_questions, 1):
        questions_text += f"{i}. {q.get('question','')}\n"
        try:
            idx = int(q.get('correct_answer', 0))
            opt = q.get('options', [])
            correct_text = opt[idx] if 0 <= idx < len(opt) else "❓"
            questions_text += f"   To'g'ri javob: {correct_text}\n\n"
        except Exception:
            questions_text += f"   To'g'ri javob: ❓\n\n"

    # Telegram xabar chegarasi (4096 belgi)
    if len(questions_text) > 4096:
        for x in range(0, len(questions_text), 4096):
            bot.send_message(message.chat.id, questions_text[x:x + 4096])
    else:
        bot.send_message(message.chat.id, questions_text)

    bot.send_message(message.chat.id, "Bosh menyu:", reply_markup=menu_keyboards())
    bot.register_next_step_handler(message, main_menu)


# ====== START / LANGUAGE / MENU ======
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.from_user.id
    username = message.from_user.username or ""
    is_admin = (str(chat_id) == str(ADMIN_ID))

    args = message.text.split()
    referred_by = None

    if len(args) > 1:
        try:
            referred_by = int(args[1])
            if referred_by == chat_id:
                referred_by = None
        except:
            referred_by = None

    is_new = db.insert_or_update_user_daily(chat_id, username, is_admin=is_admin)

    if is_new and referred_by:
        db.add_points_to_user(referred_by, 10)
        bot.send_message(
            referred_by,
            f"🎉 Yangi foydalanuvchi sizning havolangiz orqali qo'shildi!\n💰 Sizga 10 ball qo'shildi."
        )

    bot.send_message(
        chat_id,
        "Assalomu aleykum game botimizga xush kelibsiz" + ("\n🛡 Siz adminsiz." if is_admin else ""),
        reply_markup=groups_links()
    )


@bot.callback_query_handler(func=lambda call: call.data == "verify_subscription")
def verify_subscription(call):
    user_id = call.message.chat.id
    try:
        member = bot.get_chat_member(chat_id=group_username, user_id=user_id)
        if member.status in ['member', 'creator', 'administrator']:
            bot.answer_callback_query(call.id, "✅ A'zolik tasdiqlandi.")
            choose_languange(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Siz hali a'zo emassiz.")
            bot.send_message(user_id, "❌ Siz hali kanallarga a'zo bo'lmadingiz.")
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Xatolik yuz berdi.")
        bot.send_message(user_id, f"Xatolik: {e}")


def choose_languange(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Tillni tanlang", reply_markup=generate_language())


@bot.callback_query_handler(func=lambda call: call.data in ["uz", "en", "ru"])
def Language(call):
    chat_id = call.message.chat.id
    if call.data == "uz":
        bot.send_message(chat_id, "Siz uzbek tilini tanladingiz")
    elif call.data == "en":
        bot.send_message(chat_id, "Siz engilish tilini tanladingiz")
    elif call.data == "ru":
        bot.send_message(chat_id, "Siz rus tilini tanladingiz")

    bot.send_message(chat_id, "Bosh menuga xush kelibsiz. Bo'limlardan birini tanlang", reply_markup=menu_keyboards())
    bot.register_next_step_handler(call.message, main_menu)


def menu_keyboards():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Kunlik bal", "O'yinlar")
    markup.add("Test yechish", "Do'stlarni taklif qilish")
    markup.add("Shartlar", "Ma'lumotlarni ko'rish")
    markup.add("Darajalar", "Orqaga")
    return markup


def main_menu(message):
    chat_id = message.chat.id

    invite_text = (
        "🎉 Do'stlaringizni botga taklif qiling va mukofot ballarini qo'lga kiriting!\n\n"
        "🧑‍🤝‍🧑 Har bir taklifingiz uchun sizga 10 ball beriladi.\n\n"
        "📩 Shaxsiy taklif havolangiz:\n"
        f"https://t.me/your_choice1_bot?start={chat_id}\n\n"
        "🔗 Ushbu havolani do'stlaringizga yuboring va ular botni birinchi marta ochganda siz ballga ega bo'lasiz!"
    )

    if message.text == "Kunlik bal":
        bot.send_message(chat_id, "Kunlik balingizni olib bo'ldingiz")

    elif message.text == "O'yinlar":
        bot.send_message(chat_id, "O'yin tanlang", reply_markup=games())
        bot.register_next_step_handler(message, back_game)

    elif message.text == "Test yechish":
        start_test(message)

    elif message.text == "Do'stlarni taklif qilish":
        bot.send_message(chat_id, invite_text)

    elif message.text == "Shartlar":
        bot.send_message(chat_id, "Shartlarni bajaring va ball oling")

    elif message.text == "Ma'lumotlarni ko'rish":
        show_user_info(message)

    elif message.text == "Darajalar":
        try:
            bot.send_photo(
                chat_id,
                photo=open("daraja_photo/photo_2025-08-08_21-56-34.jpg", "rb"),
                caption=(
                    "🔘 <b>Bronze</b>         0 – 999                     🔶 Boshlovchi\n"
                    "⚪ <b>Silver</b>         1,000 – 9,999               🥈 Faol ishtirokchi\n"
                    "🟡 <b>Gold</b>           10,000 – 49,999             🥇 Bot yetakchisi\n"
                    "🔴 <b>Karona</b>        50,000 – 99,999             👑 Ustoz o'yinchi\n"
                    "🟣 <b>Legend</b>        100,000 – 499,999           🌟 Afsonaviy foydalanuvchi\n"
                    "🔵 <b>Mythic</b>        500,000+                    🔥 Elita\n"
                ),
                parse_mode="HTML"
            )
        except:
            bot.send_message(
                chat_id,
                "🔘 <b>Bronze</b>         0 – 999                     🔶 Boshlovchi\n"
                "⚪ <b>Silver</b>         1,000 – 9,999               🥈 Faol ishtirokchi\n"
                "🟡 <b>Gold</b>           10,000 – 49,999             🥇 Bot yetakchisi\n"
                "🔴 <b>Karona</b>        50,000 – 99,999             👑 Ustoz o'yinchi\n"
                "🟣 <b>Legend</b>        100,000 – 499,999           🌟 Afsonaviy foydalanuvchi\n"
                "🔵 <b>Mythic</b>        500,000+                    🔥 Elita\n",
                parse_mode="HTML"
            )
    elif message.text == "Orqaga":
        bot.send_message(
            chat_id,
            "Assalomu aleykum yutib ol botimizga xush kelibsiz. Tilni tanlang!",
            reply_markup=generate_language()
        )


@bot.message_handler(func=lambda msg: msg.text == "Ma'lumotlarni ko'rish")
def show_user_info(message):
    user_chat_id = message.chat.id
    data = db.select_info(user_chat_id)

    if not data:
        bot.send_message(user_chat_id, "📂 Siz haqingizda hech qanday ma'lumot topilmadi.")
        return

    chat_id, username, points, last_daily, is_admin = data[0]
    response = (
        f"📋 Sizning ma'lumotlaringiz:\n\n"
        f"👤 Foydalanuvchi: @{username or 'Noma\'lum'}\n"
        f"🆔 ID: {chat_id}\n"
        f"🏆 Ball: {points}\n"
        f"📅 Oxirgi kirgan sana: {last_daily.strftime('%Y-%m-%d') if last_daily else 'Noma\'lum'}\n"
        f"👑 Admin: {'Ha' if is_admin else 'Yo\'q'}\n"
    )

    bot.send_message(user_chat_id, response)


# ====== CHESS (menyu va boshqaruv) ======
@bot.message_handler(func=lambda msg: msg.text == "Shaxmat")
def chess_menu(msg):
    chat_id = msg.chat.id

    if chat_id in active_players:
        game_id = active_players[chat_id]
        game = chess_games.get(game_id)
        if game and game['status'] == 'active':
            opponent_id = game['player2'] if game['player1'] == chat_id else game['player1']
            bot.send_message(chat_id, f"Siz allaqachon faol o'yindasiz! Raqibingiz: {opponent_id}")
            return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("♟ Yangi o'yin", callback_data="chess_new_game"),
        types.InlineKeyboardButton("♟ O'yin qo'shilish", callback_data="chess_join_game"),
        types.InlineKeyboardButton("♟ Mening o'yinlarim", callback_data="chess_my_games")
    )
    bot.send_message(chat_id, "Shaxmat o'yini:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("chess_"))
def handle_chess_callback(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "chess_new_game":
        game_id = str(chat_id) + str(datetime.now().timestamp())[-6:]
        chess_games[game_id] = {
            'player1': chat_id,
            'player2': None,
            'player1_color': 'white',
            'player2_color': 'black',
            'current_player': 'white',
            'status': 'waiting',
            'moves': [],
            'winner': None,
            'created_at': datetime.now()
        }
        active_players[chat_id] = game_id

        bot.send_message(
            chat_id,
            "♟ Yangi shaxmat o'yini yaratildi!\n\n"
            f"🔹 O'yin ID: {game_id}\n"
            "🔹 Siz oq rangda o'ynaysiz\n\n"
            "Do'stingizga ushbu ID ni yuboring yoki ular 'O'yin qo'shilish' tugmasini bosib o'yin ID sini kiritsin."
        )

    elif data == "chess_join_game":
        msg = bot.send_message(chat_id, "O'yin ID sini kiriting:")
        bot.register_next_step_handler(msg, process_join_game)

    elif data == "chess_my_games":
        show_user_games(call)


def process_join_game(message):
    chat_id = message.chat.id
    game_id = message.text.strip()

    if game_id not in chess_games:
        bot.send_message(chat_id, "❌ Noto'g'ri o'yin ID si! Iltimos, qayta urinib ko'ring.")
        return

    game = chess_games[game_id]

    if game['player2'] is not None:
        bot.send_message(chat_id, "❌ Bu o'yinda allaqachon 2 o'yinchi bor!")
        return

    if game['player1'] == chat_id:
        bot.send_message(chat_id, "❌ Siz o'zingizning o'yiningizga qo'sha olmaysiz!")
        return

    game['player2'] = chat_id
    game['status'] = 'active'
    active_players[chat_id] = game_id

    if random.random() > 0.5:
        game['player1_color'], game['player2_color'] = game['player2_color'], game['player1_color']
        game['current_player'] = game['player1_color']

    player1_color = "oq" if game['player1_color'] == 'white' else "qora"
    player2_color = "oq" if game['player2_color'] == 'white' else "qora"

    bot.send_message(
        game['player1'],
        "♟ O'yinchi qo'shildi! O'yin boshlandi.\n\n"
        f"🔹 Siz {player1_color} rangda o'ynaysiz\n"
        f"🔹 Raqibingiz: @{message.from_user.username or 'noma\'lum'}\n\n"
        "O'yinni boshlash uchun pastdagi tugmani bosing:"
    )

    bot.send_message(
        chat_id,
        "♟ Siz o'yin qo'shildingiz! O'yin boshlandi.\n\n"
        f"🔹 Siz {player2_color} rangda o'ynaysiz\n"
        "O'yinni boshlash uchun pastdagi tugmani bosing:"
    )

    # Send chess board links to both players
    webapp_markup = types.InlineKeyboardMarkup()
    webapp_markup.add(create_webapp_button(game_id, game['player1'], "chess"))
    bot.send_message(game['player1'], "O'yin doskasini ochish uchun:", reply_markup=webapp_markup)

    webapp_markup = types.InlineKeyboardMarkup()
    webapp_markup.add(create_webapp_button(game_id, chat_id, "chess"))
    bot.send_message(chat_id, "O'yin doskasini ochish uchun:", reply_markup=webapp_markup)


def show_user_games(call):
    chat_id = call.message.chat.id
    user_games = []

    for game_id, game in chess_games.items():
        if game['player1'] == chat_id or game['player2'] == chat_id:
            user_games.append((game_id, game))

    if not user_games:
        bot.send_message(chat_id, "Sizda hozircha faol o'yinlar yo'q.")
        return

    markup = types.InlineKeyboardMarkup()
    for game_id, game in user_games:
        status = "🔵 Faol" if game['status'] == 'active' else ("🟢 Kutilmoqda" if game['status'] == 'waiting' else "🔴 Tugagan")
        markup.add(types.InlineKeyboardButton(
            text=f"O'yin {game_id} ({status})",
            callback_data=f"chess_view_{game_id}"
        ))

    bot.send_message(chat_id, "Sizning o'yinlaringiz:", reply_markup=markup)


# ====== SHASHKA (menyu va boshqaruv) ======
@bot.message_handler(func=lambda msg: msg.text == "Shashka")
def shashka_menu(msg):
    chat_id = msg.chat.id

    if chat_id in shashka_active_players:
        game_id = shashka_active_players[chat_id]
        game = shashka_games.get(game_id)
        if game and game['status'] == 'active':
            opponent_id = game['player2'] if game['player1'] == chat_id else game['player1']
            bot.send_message(chat_id, f"Siz allaqachon faol shashka o'yindasiz! Raqibingiz: {opponent_id}")
            return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔴 Yangi o'yin", callback_data="shashka_new_game"),
        types.InlineKeyboardButton("⚪ O'yin qo'shilish", callback_data="shashka_join_game"),
        types.InlineKeyboardButton("📋 Mening o'yinlarim", callback_data="shashka_my_games")
    )
    bot.send_message(chat_id, "Shashka (Rus damasi) o'yini:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("shashka_"))
def handle_shashka_callback(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "shashka_new_game":
        game_id = "sh_" + str(chat_id) + str(int(datetime.now().timestamp()))[-6:]
        shashka_games[game_id] = {
            'player1': chat_id,
            'player2': None,
            'player1_color': 'white',
            'player2_color': 'black',
            'current_player': 'white',
            'status': 'waiting',
            'moves': [],
            'winner': None,
            'created_at': datetime.now()
        }
        shashka_active_players[chat_id] = game_id

        bot.send_message(chat_id,
            "🔴 Yangi shashka o'yini yaratildi!\n\n"
            f"🔹 O'yin ID: {game_id}\n"
            "🔹 Siz oq rangda (🔴) boshlaysiz\n\n"
            "Do'stingizga ushbu ID ni yuboring yoki ular 'O'yin qo'shilish' tugmasini bosib o'yin ID sini kiritsin."
        )

    elif data == "shashka_join_game":
        msg = bot.send_message(chat_id, "O'yin ID sini kiriting:")
        bot.register_next_step_handler(msg, process_shashka_join_game)

    elif data == "shashka_my_games":
        show_shashka_user_games(call)


def process_shashka_join_game(message):
    chat_id = message.chat.id
    game_id = message.text.strip()

    if game_id not in shashka_games:
        bot.send_message(chat_id, "❌ Noto'g'ri o'yin ID si! Iltimos, qayta urinib ko'ring.")
        return

    game = shashka_games[game_id]

    if game['player2'] is not None:
        bot.send_message(chat_id, "❌ Bu o'yinda allaqachon 2 o'yinchi bor!")
        return

    if game['player1'] == chat_id:
        bot.send_message(chat_id, "❌ Siz o'zingizning o'yiningizga qo'sha olmaysiz!")
        return

    game['player2'] = chat_id
    game['status'] = 'active'
    shashka_active_players[chat_id] = game_id

    if random.random() > 0.5:
        game['player1_color'], game['player2_color'] = game['player2_color'], game['player1_color']
        game['current_player'] = game['player1_color']

    player1_color = "oq (🔴)" if game['player1_color'] == 'white' else "qora (⚪)"
    player2_color = "oq (🔴)" if game['player2_color'] == 'white' else "qora (⚪)"

    bot.send_message(
        game['player1'],
        "🔴⚪ Shashka o'yinchi qo'shildi! O'yin boshlandi.\n\n"
        f"🔹 Siz {player1_color} rangda o'ynaysiz\n"
        f"🔹 Raqibingiz: @{message.from_user.username or 'noma\'lum'}\n\n"
        "O'yinni boshlash uchun pastdagi tugmani bosing:"
    )

    bot.send_message(
        chat_id,
        "🔴⚪ Siz shashka o'yiniga qo'shildingiz! O'yin boshlandi.\n\n"
        f"🔹 Siz {player2_color} rangda o'ynaysiz\n"
        "O'yinni boshlash uchun pastdagi tugmani bosing:"
    )

    # Send shashka board links to both players
    webapp_markup = types.InlineKeyboardMarkup()
    webapp_markup.add(create_webapp_button(game_id, game['player1'], "shashka"))
    bot.send_message(game['player1'], "O'yin doskasini ochish uchun:", reply_markup=webapp_markup)

    webapp_markup = types.InlineKeyboardMarkup()
    webapp_markup.add(create_webapp_button(game_id, chat_id, "shashka"))
    bot.send_message(chat_id, "O'yin doskasini ochish uchun:", reply_markup=webapp_markup)


def show_shashka_user_games(call):
    chat_id = call.message.chat.id
    user_games = []

    for game_id, game in shashka_games.items():
        if game['player1'] == chat_id or game['player2'] == chat_id:
            user_games.append((game_id, game))

    if not user_games:
        bot.send_message(chat_id, "Sizda hozircha faol shashka o'yinlari yo'q.")
        return

    markup = types.InlineKeyboardMarkup()
    for game_id, game in user_games:
        status = "🔵 Faol" if game['status'] == 'active' else ("🟢 Kutilmoqda" if game['status'] == 'waiting' else "🔴 Tugagan")
        markup.add(types.InlineKeyboardButton(
            text=f"Shashka {game_id} ({status})",
            callback_data=f"shashka_view_{game_id}"
        ))

    bot.send_message(chat_id, "Sizning shashka o'yinlaringiz:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text and message.text.startswith("/shashka_move_"))
def handle_shashka_move(message):
    try:
        parts = message.text.split('_')
        game_id = parts[2]
        move = parts[3]
        player_id = message.chat.id

        if game_id not in shashka_games:
            bot.send_message(player_id, "❌ O'yin topilmadi!")
            return

        game = shashka_games[game_id]

        if game['status'] != 'active':
            bot.send_message(player_id, "❌ Bu o'yin allaqachon tugagan!")
            return

        # Check turn
        player_color = None
        if game['player1'] == player_id:
            player_color = game['player1_color']
        elif game['player2'] == player_id:
            player_color = game['player2_color']
        else:
            bot.send_message(player_id, "❌ Siz bu o'yinda o'ynay olmaysiz!")
            return

        if player_color != game['current_player']:
            bot.send_message(player_id, "❌ Sizning navbatingiz emas!")
            return

        game['moves'].append(move)
        game['current_player'] = 'black' if game['current_player'] == 'white' else 'white'

        opponent_id = game['player2'] if game['player1'] == player_id else game['player1']
        bot.send_message(opponent_id, f"🔴⚪ Raqibingiz yangi harakat qildi!\n\nHarakat: {move}\n\nSizning navbatingiz!")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik yuz berdi: {str(e)}")


@bot.message_handler(func=lambda message: message.text and message.text.startswith("/shashka_end_"))
def handle_shashka_end(message):
    try:
        parts = message.text.split('_')
        game_id = parts[2]
        winner_id = int(parts[3])
        player_id = message.chat.id

        if game_id not in shashka_games:
            bot.send_message(player_id, "❌ O'yin topilmadi!")
            return

        game = shashka_games[game_id]

        if game['status'] != 'active':
            bot.send_message(player_id, "❌ Bu o'yin allaqachon tugagan!")
            return

        if player_id not in [game['player1'], game['player2']]:
            bot.send_message(player_id, "❌ Siz bu o'yinda o'ynay olmaysiz!")
            return

        game['status'] = 'finished'
        game['winner'] = winner_id

        if game['player1'] in shashka_active_players:
            del shashka_active_players[game['player1']]
        if game['player2'] in shashka_active_players:
            del shashka_active_players[game['player2']]

        if winner_id != 0:
            try:
                db.add_points_to_user(winner_id, 10)
            except Exception as e:
                print(f"DB add points error (shashka): {e}")

        if winner_id == 0:
            result_text = "🔴⚪ O'yin durrang bilan yakunlandi!"
        else:
            result_text = f"🎉 O'yin yakunlandi! G'olib: {winner_id}\n💰 G'olibga 10 ball qo'shildi!"

        bot.send_message(game['player1'], result_text)
        bot.send_message(game['player2'], result_text)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik yuz berdi: {str(e)}")


# ====== Orqaga ======
def back_game(message):
    chat_id = message.chat.id
    if message.text == "Orqaga":
        bot.send_message(chat_id, "Bosh menu ga qaytingiz — bo'limlardan birini tanlang", reply_markup=menu_keyboards())
        bot.register_next_step_handler(message, main_menu)


# ====== Run ======
if __name__ == "__main__":
    load_test_questions()
    bot.polling(non_stop=True)
