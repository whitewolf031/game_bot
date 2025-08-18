import os
from telebot import TeleBot
from dotenv import load_dotenv
from db.user_info_db import User_info
from keyboards import *
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

load_dotenv()

token = os.getenv('TOKEN')
bot = TeleBot(token)
ADMIN_ID = os.getenv("ADMIN_ID")
group_username = '@codecraftdevelop'
db = User_info()
user_info = {}

# Chess game states
chess_games = {}  # Format: {game_id: {'player1': user_id, 'player2': user_id, 'scores': {'white': 0, 'black': 0}, 'current_turn': 'white'}}
active_players = {}  # {user_id: game_id}
link = "https://whitewolf031.github.io/game_bot/web_app/chess.html"

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.from_user.id
    username = message.from_user.username or ""
    is_admin = (chat_id == ADMIN_ID)

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
            f"🎉 Yangi foydalanuvchi sizning havolangiz orqali qo‘shildi!\n💰 Sizga 10 ball qo‘shildi."
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

    if message.text == "O'yinlar":
        bot.send_message(chat_id, "O'yin tanlang", reply_markup=games())
        bot.register_next_step_handler(message, back_game)

    if message.text == "Do'stlarni taklif qilish":
        bot.send_message(chat_id, invite_text)

    if message.text == "Shartlar":
        bot.send_message(chat_id, "Shartlarni bajaring va ball oling")

    if message.text == "Ma'lumotlarni ko'rish":
        bot.send_message(chat_id, "Sizning ma'lumotlaringiz")

    if message.text == "Darajalar":
        bot.send_photo(chat_id, photo=open("daraja_photo/photo_2025-08-08_21-56-34.jpg", "rb"), caption=
        "🔘 <b>Bronze</b>         0 – 999                     🔶 Boshlovchi\n"
        "⚪ <b>Silver</b>         1,000 – 9,999               🥈 Faol ishtirokchi\n"
        "🟡 <b>Gold</b>           10,000 – 49,999             🥇 Bot yetakchisi\n"
        "🔴 <b>Karona</b>        50,000 – 99,999             👑 Ustoz o'yinchi\n"
        "🟣 <b>Legend</b>        100,000 – 499,999           🌟 Afsonaviy foydalanuvchi\n"
        "🔵 <b>Mythic</b>        500,000+                          🔥 Elita\n",
                       parse_mode="HTML")
    elif message.text == "Orqaga":
        bot.send_message(chat_id, "Assalomu aleykum yutib ol botimizga xush kelibsiz. Tilni tanlang!",
                         reply_markup=generate_language())

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
        f"👤 Foydalanuvchi: @{username or 'Noma`lum'}\n"
        f"🆔 ID: {chat_id}\n"
        f"🏆 Ball: {points}\n"
        f"📅 Oxirgi kirgan sana: {last_daily.strftime('%Y-%m-%d') if last_daily else 'Noma`lum'}\n"
        f"👑 Admin: {'Ha' if is_admin else 'Yo`q'}\n"
    )

    bot.send_message(user_chat_id, response)


@bot.message_handler(func=lambda msg: msg.text == "Shaxmat")
def chess_menu(msg):
    chat_id = msg.chat.id

    # Check if user is already in a game
    if chat_id in active_players:
        game_id = active_players[chat_id]
        game = chess_games.get(game_id)
        if game:
            opponent_id = game['player2'] if game['player1'] == chat_id else game['player1']
            bot.send_message(chat_id, f"Siz allaqachon o'yinda siz! Opponent: {opponent_id}")
            return

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("♟ Yangi o'yin", callback_data="chess_new_game"),
        InlineKeyboardButton("♟ O'yin qo'shilish", callback_data="chess_join_game"),
        InlineKeyboardButton("♟ O'yinni ochish",
                             web_app=WebAppInfo(url=link))
    )
    bot.send_message(chat_id, "Shaxmat o'yini:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("chess_"))
def handle_chess_callback(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "chess_new_game":
        # Create new game
        game_id = str(chat_id) + str(datetime.now().timestamp())
        chess_games[game_id] = {
            'player1': chat_id,
            'player2': None,
            'scores': {'white': 0, 'black': 0},
            'current_turn': 'white'
        }
        active_players[chat_id] = game_id

        bot.send_message(chat_id, f"Yangi shaxmat o'yini yaratildi! O'yin ID: {game_id}\n"
                                  f"Do'stingizga ushbu ID ni yuboring yoki ular 'O'yin qo'shilish' tugmasini bosib o'yin ID sini kiritsin.")

    elif data == "chess_join_game":
        msg = bot.send_message(chat_id, "O'yin ID sini kiriting:")
        bot.register_next_step_handler(msg, process_join_game)


def process_join_game(message):
    chat_id = message.chat.id
    game_id = message.text

    if game_id not in chess_games:
        bot.send_message(chat_id, "Noto'g'ri o'yin ID si! Iltimos, qayta urinib ko'ring.")
        return

    game = chess_games[game_id]

    if game['player2'] is not None:
        bot.send_message(chat_id, "Bu o'yinda allaqachon 2 o'yinchi bor!")
        return

    if game['player1'] == chat_id:
        bot.send_message(chat_id, "Siz o'zingizning o'yiningizga qo'sha olmaysiz!")
        return

    # Join the game
    game['player2'] = chat_id
    active_players[chat_id] = game_id

    # Notify both players
    bot.send_message(game['player1'],
                     f"O'yinchi qo'shildi! O'yin boshlandi.\nSiz {'oq' if game['current_turn'] == 'white' else 'qora'} bilan o'ynaysiz.")
    bot.send_message(chat_id,
                     f"Siz o'yin qo'shildingiz! O'yin boshlandi.\nSiz {'oq' if game['current_turn'] == 'black' else 'qora'} bilan o'ynaysiz.")

    # Send chess board
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(
        text="♟ O'yinni ochish",
        web_app=WebAppInfo(url="https://whitewolf031.github.io/game_bot/web_app/chess.html")
    ))
    bot.send_message(game['player1'], "Shaxmat doskasini ochish uchun:", reply_markup=markup)
    bot.send_message(chat_id, "Shaxmat doskasini ochish uchun:", reply_markup=markup)


def back_game(message):
    chat_id = message.chat.id
    if message.text == "Orqaga":
        bot.send_message(chat_id, "Bosh menu ga qaytingiz bo'limlardan birini tanlang", reply_markup=menu_keyboards())
        bot.register_next_step_handler(message, main_menu)


bot.polling(non_stop=True)