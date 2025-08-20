import os
from telebot import TeleBot, types
from dotenv import load_dotenv
from db.user_info_db import User_info
from keyboards import *
from datetime import datetime
import random

load_dotenv()

token = os.getenv('TOKEN')
bot = TeleBot(token)
ADMIN_ID = os.getenv("ADMIN_ID")
group_username = '@codecraftdevelop'
db = User_info()

# Chess game states
chess_games = {}  # Format: {game_id: {'player1': user_id, 'player2': user_id, 'board': [], 'current_player': 'white', 'player1_color': 'white', 'player2_color': 'black', 'status': 'waiting'/'active'/'finished', 'winner': None}}
active_players = {}  # {user_id: game_id}
chess_webapp_url = "https://whitewolf031.github.io/game_bot/web_app/chess.html"

# Shashka game states
shashka_games = {}  # Format: {game_id: {'player1': user_id, 'player2': user_id, 'current_player': 'white', 'player1_color': 'white', 'player2_color': 'black', 'status': 'waiting'/'active'/'finished', 'winner': None}}
shashka_active_players = {}  # {user_id: game_id}
shashka_webapp_url = "https://whitewolf031.github.io/game_bot/web_app/shashka.html"

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

@bot.callback_query_handler(func=lambda call: call.data in ["uz","en","ru"])
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

    elif message.text == "O'yinlar":
        bot.send_message(chat_id, "O'yin tanlang", reply_markup=games())
        bot.register_next_step_handler(message, back_game)

    elif message.text == "Do'stlarni taklif qilish":
        bot.send_message(chat_id, invite_text)

    elif message.text == "Shartlar":
        bot.send_message(chat_id, "Shartlarni bajaring va ball oling")

    elif message.text == "Ma'lumotlarni ko'rish":
        show_user_info(message)

    elif message.text == "Darajalar":
        bot.send_photo(chat_id, photo=open("daraja_photo/photo_2025-08-08_21-56-34.jpg", "rb"), caption=
        "🔘 <b>Bronze</b>         0 – 999                     🔶 Boshlovchi\n"
        "⚪ <b>Silver</b>         1,000 – 9,999               🥈 Faol ishtirokchi\n"
        "🟡 <b>Gold</b>           10,000 – 49,999             🥇 Bot yetakchisi\n"
        "🔴 <b>Karona</b>        50,000 – 99,999             👑 Ustoz o'yinchi\n"
        "🟣 <b>Legend</b>        100,000 – 499,999           🌟 Afsonaviy foydalanuvchi\n"
        "🔵 <b>Mythic</b>        500,000+                          🔥 Elita\n" ,
        parse_mode = "HTML")
    elif message.text == "Orqaga":
        bot.send_message(chat_id, "Assalomu aleykum yutib ol botimizga xush kelibsiz. Tilni tanlang!", reply_markup=generate_language())

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
        f"📅 Oxirgi kirgan sana: {last_daily.strftime('%Y-%m-%d') if last_daily else "Noma'lum"}\n"
        f"👑 Admin: {'Ha' if is_admin else "Yo'q"}\n"
    )

    bot.send_message(user_chat_id, response)

@bot.message_handler(func=lambda msg: msg.text == "Shaxmat")
def chess_menu(msg):
    chat_id = msg.chat.id

    # Check if user is already in a game
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
        # Create new game
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

        bot.send_message(chat_id, f"♟ Yangi shaxmat o'yini yaratildi!\n\n"
                                  f"🔹 O'yin ID: {game_id}\n"
                                  f"🔹 Siz oq rangda o'ynaysiz\n\n"
                                  f"Do'stingizga ushbu ID ni yuboring yoki ular 'O'yin qo'shilish' tugmasini bosib o'yin ID sini kiritsin.")

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

    # Join the game
    game['player2'] = chat_id
    game['status'] = 'active'
    active_players[chat_id] = game_id

    # Randomize colors (50% chance to swap)
    if random.random() > 0.5:
        game['player1_color'], game['player2_color'] = game['player2_color'], game['player1_color']
        game['current_player'] = game['player1_color']

    # Notify both players
    player1_color = "oq" if game['player1_color'] == 'white' else "qora"
    player2_color = "oq" if game['player2_color'] == 'white' else "qora"

    # Send to player 1
    bot.send_message(game['player1'],
                     f"♟ O'yinchi qo'shildi! O'yin boshlandi.\n\n"
                     f"🔹 Siz {player1_color} rangda o'ynaysiz\n"
                     f"🔹 Raqibingiz: @{message.from_user.username or "noma'lum"}\n\n"
                     f"O'yinni boshlash uchun pastdagi tugmani bosing:")

    # Send to player 2
    bot.send_message(chat_id,
                     f"♟ Siz o'yin qo'shildingiz! O'yin boshlandi.\n\n"
                     f"🔹 Siz {player2_color} rangda o'ynaysiz\n"
                     f"🔹 Raqibingiz: @{bot.get_chat_member(game['player1'], game['player1']).user.username or "noma'lum"}\n\n"
                     f"O'yinni boshlash uchun pastdagi tugmani bosing:")

    # Send chess board links to both players
    webapp_markup = types.InlineKeyboardMarkup()
    webapp_markup.add(types.InlineKeyboardButton(
        text="♟ O'yinni boshlash",
        web_app=types.WebAppInfo(url=f"{chess_webapp_url}?game_id={game_id}&player_id={game['player1']}")
    ))
    bot.send_message(game['player1'], "O'yin doskasini ochish uchun:", reply_markup=webapp_markup)

    webapp_markup = types.InlineKeyboardMarkup()
    webapp_markup.add(types.InlineKeyboardButton(
        text="♟ O'yinni boshlash",
        web_app=types.WebAppInfo(url=f"{chess_webapp_url}?game_id={game_id}&player_id={chat_id}")
    ))
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
        opponent_id = game['player2'] if game['player1'] == chat_id else game['player1']
        status = "🔵 Faol" if game['status'] == 'active' else "🟢 Kutilmoqda" if game['status'] == 'waiting' else "🔴 Tugagan"

        markup.add(types.InlineKeyboardButton(
            text=f"O'yin {game_id} ({status})",
            callback_data=f"chess_view_{game_id}"
        ))

    bot.send_message(chat_id, "Sizning o'yinlaringiz:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text and message.text.startswith("/move_"))
def handle_chess_move(message):
    try:
        parts = message.text.split('_')
        game_id = parts[1]
        move = parts[2]
        player_id = message.chat.id

        if game_id not in chess_games:
            bot.send_message(player_id, "❌ O'yin topilmadi!")
            return

        game = chess_games[game_id]

        if game['status'] != 'active':
            bot.send_message(player_id, "❌ Bu o'yin allaqachon tugagan!")
            return

        # Check if it's player's turn
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

        # Process the move (simplified - in a real game you'd validate the move)
        game['moves'].append(move)
        game['current_player'] = 'black' if game['current_player'] == 'white' else 'white'

        # Notify opponent
        opponent_id = game['player2'] if game['player1'] == player_id else game['player1']
        bot.send_message(opponent_id, f"♟ Raqibingiz yangi harakat qildi!\n\nHarakat: {move}\n\nSizning navbatingiz!")

        # Check for game end conditions (simplified)
        # In a real game, you'd check for checkmate, stalemate, etc.

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik yuz berdi: {str(e)}")

@bot.message_handler(func=lambda message: message.text and message.text.startswith("/endgame_"))
def handle_game_end(message):
    try:
        parts = message.text.split('_')
        game_id = parts[1]
        winner_id = int(parts[2])
        player_id = message.chat.id

        if game_id not in chess_games:
            bot.send_message(player_id, "❌ O'yin topilmadi!")
            return

        game = chess_games[game_id]

        if game['status'] != 'active':
            bot.send_message(player_id, "❌ Bu o'yin allaqachon tugagan!")
            return

        # Check if player is in this game
        if player_id not in [game['player1'], game['player2']]:
            bot.send_message(player_id, "❌ Siz bu o'yinda o'ynay olmaysiz!")
            return

        # End the game
        game['status'] = 'finished'
        game['winner'] = winner_id

        # Remove from active players
        if game['player1'] in active_players:
            del active_players[game['player1']]
        if game['player2'] in active_players:
            del active_players[game['player2']]

        # Award points to winner
        if winner_id != 0:  # 0 means draw
            db.add_points_to_user(winner_id, 10)

        # Notify both players
        if winner_id == 0:
            result_text = "O'yin durrang bilan yakunlandi!"
        else:
            winner_username = bot.get_chat_member(winner_id, winner_id).user.username
            result_text = f"🎉 O'yin yakunlandi! G'olib: @{winner_username or "noma'lum"}\n💰 G'olibga 10 ball qo'shildi!"

            bot.send_message(game['player1'], result_text)
            bot.send_message(game['player2'], result_text)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik yuz berdi: {str(e)}")

@bot.message_handler(func=lambda msg: msg.text == "Shashka")
def shashka_menu(msg):
    chat_id = msg.chat.id

    # Check if user is already in a game
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
        # Create new game
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

        bot.send_message(chat_id, f"🔴 Yangi shashka o'yini yaratildi!\n\n"
                                  f"🔹 O'yin ID: {game_id}\n"
                                  f"🔹 Siz oq rangda (🔴) boshlaysiz\n\n"
                                  f"Do'stingizga ushbu ID ni yuboring yoki ular 'O'yin qo'shilish' tugmasini bosib o'yin ID sini kiritsin.")

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

    # Join the game
    game['player2'] = chat_id
    game['status'] = 'active'
    shashka_active_players[chat_id] = game_id

    # Randomize colors (50% chance to swap)
    if random.random() > 0.5:
        game['player1_color'], game['player2_color'] = game['player2_color'], game['player1_color']
        game['current_player'] = game['player1_color']

    # Notify both players
    player1_color = "oq (🔴)" if game['player1_color'] == 'white' else "qora (⚪)"
    player2_color = "oq (🔴)" if game['player2_color'] == 'white' else "qora (⚪)"

    # Send to player 1
    bot.send_message(game['player1'],
                     f"🔴⚪ Shashka o'yinchi qo'shildi! O'yin boshlandi.\n\n"
                     f"🔹 Siz {player1_color} rangda o'ynaysiz\n"
                     f"🔹 Raqibingiz: @{message.from_user.username or "noma'lum"}\n\n"
                     f"O'yinni boshlash uchun pastdagi tugmani bosing:")

    # Send to player 2
    bot.send_message(chat_id,
                     f"🔴⚪ Siz shashka o'yiniga qo'shildingiz! O'yin boshlandi.\n\n"
                     f"🔹 Siz {player2_color} rangda o'ynaysiz\n"
                     f"🔹 Raqibingiz: @{bot.get_chat_member(game['player1'], game['player1']).user.username or "noma'lum"}\n\n"
                     f"O'yinni boshlash uchun pastdagi tugmani bosing:")

    # Send shashka board links to both players
    webapp_markup = types.InlineKeyboardMarkup()
    webapp_markup.add(types.InlineKeyboardButton(
        text="🔴⚪ O'yinni boshlash",
        web_app=types.WebAppInfo(url=f"{shashka_webapp_url}?game_id={game_id}&player_id={game['player1']}")
    ))
    bot.send_message(game['player1'], "O'yin doskasini ochish uchun:", reply_markup=webapp_markup)

    webapp_markup = types.InlineKeyboardMarkup()
    webapp_markup.add(types.InlineKeyboardButton(
        text="🔴⚪ O'yinni boshlash",
        web_app=types.WebAppInfo(url=f"{shashka_webapp_url}?game_id={game_id}&player_id={chat_id}")
    ))
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
        opponent_id = game['player2'] if game['player1'] == chat_id else game['player1']
        status = "🔵 Faol" if game['status'] == 'active' else "🟢 Kutilmoqda" if game['status'] == 'waiting' else "🔴 Tugagan"

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

        # Check if it's player's turn
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

        # Process the move
        game['moves'].append(move)
        game['current_player'] = 'black' if game['current_player'] == 'white' else 'white'

        # Notify opponent
        opponent_id = game['player2'] if game['player1'] == player_id else game['player1']
        bot.send_message(opponent_id, f"🔴⚪ Raqibingiz yangi harakat qildi!\n\nHarakat: {move}\n\nSizning navbatingiz!")

        # Check for game end conditions
        # In a real implementation, you'd check if the game is over

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

        # Check if player is in this game
        if player_id not in [game['player1'], game['player2']]:
            bot.send_message(player_id, "❌ Siz bu o'yinda o'ynay olmaysiz!")
            return

        # End the game
        game['status'] = 'finished'
        game['winner'] = winner_id

        # Remove from active players
        if game['player1'] in shashka_active_players:
            del shashka_active_players[game['player1']]
        if game['player2'] in shashka_active_players:
            del shashka_active_players[game['player2']]

        # Award points to winner
        if winner_id != 0:  # 0 means draw
            db.add_points_to_user(winner_id, 10)

        # Notify both players
        if winner_id == 0:
            result_text = "🔴⚪ O'yin durrang bilan yakunlandi!"
        else:
            winner_username = bot.get_chat_member(winner_id, winner_id).user.username
            result_text = f"🎉 O'yin yakunlandi! G'olib: @{winner_username or "noma'lum"}\n💰 G'olibga 10 ball qo'shildi!"

            bot.send_message(game['player1'], result_text)
            bot.send_message(game['player2'], result_text)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik yuz berdi: {str(e)}")

def back_game(message):
    chat_id = message.chat.id
    if message.text == "Orqaga":
        bot.send_message(chat_id, "Bosh menu ga qaytingiz bo'limlardan birini tanlang", reply_markup=menu_keyboards())
        bot.register_next_step_handler(message, main_menu)

bot.polling(non_stop=True)