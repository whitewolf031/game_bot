from telebot import types

Group_url = 'https://t.me/codecraftdevelop'


def generate_language():
    keyboard = types.InlineKeyboardMarkup()
    btn_uz = types.InlineKeyboardButton(text="🇺🇿Uz", callback_data="uz")
    btn_en = types.InlineKeyboardButton(text="🇺🇸En", callback_data="en")
    btn_ru = types.InlineKeyboardButton(text="🇷🇺Ru", callback_data="ru")
    keyboard.row(btn_uz, btn_en, btn_ru)
    return keyboard

def groups_links():
    keyboard = types.InlineKeyboardMarkup()
    btn_group1 = types.InlineKeyboardButton(text="Group name", url=Group_url)
    btn_check = types.InlineKeyboardButton("✅ Tekshirish", callback_data="verify_subscription")
    keyboard.row(btn_group1)
    keyboard.row(btn_check)
    return keyboard

def menu_keyboards():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_ball = types.KeyboardButton("Kunlik bal")
    btn_game = types.KeyboardButton("O'yinlar")
    btn_offer = types.KeyboardButton("Do'stlarni taklif qilish")
    btn_conditions = types.KeyboardButton("Shartlar")
    btn_check = types.KeyboardButton("Ma'lumotlarni ko‘rish")
    btn_back = types.KeyboardButton("Orqaga")

    keyboard.row(btn_ball, btn_game)
    keyboard.row(btn_offer, btn_conditions)
    keyboard.row(btn_check)
    keyboard.row(btn_back)
    return keyboard

def games():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_chess = types.KeyboardButton("Shaxmat")
    btn_shashka = types.KeyboardButton("Shashka")
    keyboard.row(btn_chess, btn_shashka)
    return keyboard