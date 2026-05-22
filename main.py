import asyncio
import os
import sqlite3
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = os.getenv("BOT_TOKEN")
# Используем ваш рабочий ключ напрямую в коде
GEMINI_API_KEY = "AIzaSyB0zIZUYnpZlIplpx0chWIU46pSNWsfAms"

# ==========================================
# ВАШИ НАСТРОЙКИ (ID проверены и вписаны)
# ==========================================
ADMIN_ID = 269215305  # Ваш ID
MOM_ID = 5599753365    # ID мамы

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

# ==========================================
# РАБОТА С БАЗОЙ ДАННЫХ (SQLite)
# ==========================================
DB_PATH = "medbot_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Таблица для лекарств
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            time TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# СОСТОЯНИЯ (FSM)
# ==========================================
class ChatStates(StatesGroup):
    waiting_for_mom_question = State()
    waiting_for_son_reply = State()
    waiting_for_ingredients = State()
    # Состояния для админки
    waiting_for_pill_name = State()
    waiting_for_pill_time = State()

# ==========================================
# КЛАВИАТУРЫ
# ==========================================
def get_mom_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🥘 Что приготовить из холодильника?")],
            [KeyboardButton(text="❓ Задать вопрос сыну")]
        ],
        resize_keyboard=True, persistent=True
    )

# ==========================================
# АДМИН-ФУНКЦИИ (УПРАВЛЕНИЕ ЛЕКАРСТВАМИ)
# ==========================================

# Посмотреть список всех лекарств
@dp.message(Command("pills"))
async def list_pills(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, time FROM pills ORDER BY time ASC")
    pills = cursor.fetchall()
    conn.close()
    
    if not pills:
        await message.answer("📋 Список лекарств пуст. Используйте /add_pill чтобы добавить.")
        return
        
    text = "📋 **Текущий список лекарств:**\n\n"
    for p in pills:
        text += f"🆔 {p[0]} | ⏰ {p[1]} — **{p[2]}**\n"
    text += "\nЧтобы удалить лекарство, введите: `/del_pill ID` (например, `/del_pill 1`)"
    await message.answer(text, parse_mode="Markdown")

# Начать добавление лекарства
@dp.message(Command("add_pill"))
async def add_pill_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.set_state(ChatStates.waiting_for_pill_name)
    await message.answer("✍️ Введите название лекарства и дозировку:\n(Например: *Омепразол 20 мг*)")

@dp.message(ChatStates.waiting_for_pill_name)
async def add_pill_name(message: types.Message, state: FSMContext):
    await state.update_data(pill_name=message.text)
    await state.set_state(ChatStates.waiting_for_pill_time)
    await message.answer("⏰ Введите время приема в формате ЧЧ:ММ по Ташкенту:\n(Например: *09:00* или *14:30*)")

@dp.message(ChatStates.waiting_for_pill_time)
async def add_pill_save(message: types.Message, state: FSMContext):
    time_text = message.text.strip()
    if len(time_text) != 5 or ":" not in time_text:
        await message.answer("⚠️ Неверный формат. Введите время как ЧЧ:ММ (например, 18:15):")
        return
        
    user_data = await state.get_data()
    pill_name = user_data['pill_name']
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pills (name, time) VALUES (?, ?)", (pill_name, time_text))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ Лекарство успешно добавлено!\n💊 {pill_name} в {time_text}\n\n*Расписание обновится при следующем запуске бота.*")
    await state.clear()

# Удаление лекарства по ID
@dp.message(Command("del_pill"))
async def delete_pill(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Укажите ID лекарства. Пример: `/del_pill 3`")
        return
        
    pill_id = args[1]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pills WHERE id = ?", (pill_id,))
    conn.commit()
    conn.close()
    
    await message.answer(f"🗑️ Лекарство с ID {pill_id} удалено из базы данных.")

# ==========================================
# АВТОМАТИЧЕСКИЕ НАПОМИНАНИЯ (ТАЙМЕРЫ)
# ==========================================

# Динамическая отправка лекарств из базы данных
async def check_and_send_pills():
    from datetime import datetime
    now = datetime.now().strftime("%H:%M")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM pills WHERE time = ?", (now,))
    pills = cursor.fetchall()
    conn.close()
    
    for pill in pills:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Приняла", callback_data=f"took_pill_{pill[0]}")]
        ])
        try:
            await bot.send_message(
                chat_id=MOM_ID, 
                text=f"💊 Мама, время принять лекарство:\n\n👉 **{pill[0]}**", 
                reply_markup=keyboard, parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Ошибка отправки таблеток: {e}")

# Универсальный обработчик нажатия кнопки "Приняла таблетку"
@dp.callback_query(F.data.startswith("took_pill_"))
async def pill_callback_handler(callback: types.CallbackQuery):
    pill_name = callback.data.replace("took_pill_", "")
    await callback.message.edit_text(f"💊 {pill_name} — ✅ Принято! Молодец, мамуля ❤️")
    await bot.send_message(chat_id=ADMIN_ID, text=f"✅ Мама только что приняла лекарство: *{pill_name}*!", parse_mode="Markdown")
    await callback.answer()

# Функция напоминания о ЕДЕ
async def send_food_reminder(meal_name: str):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍽️ Покушала", callback_data=f"ate_food_{meal_name}")]
    ])
    try:
        await bot.send_message(
            chat_id=MOM_ID,
            text=f"🍽️ Мама, время кушать! \n\n👉 Наступило время для: **{meal_name}**.",
            reply_markup=keyboard, parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Ошибка отправки еды: {e}")

# Обработчик нажатия кнопки "Покушала"
@dp.callback_query(F.data.startswith("ate_food_"))
async def food_callback_handler(callback: types.CallbackQuery):
    meal_name = callback.data.replace("ate_food_", "")
    await callback.message.edit_text(f"🍽️ {meal_name} — ✅ Выполнено! Приятного аппетита, мамуля ❤️")
    await bot.send_message(chat_id=ADMIN_ID, text=f"🍽️ Мама отметила прием пищи: *{meal_name}*!", parse_mode="Markdown")
    await callback.answer()

# ==========================================
# ИНТЕГРАЦИЯ С GEMINI AI (ОБНОВЛЕННАЯ С КЛЮЧОМ)
# ==========================================
async def ask_gemini_recipe(ingredients: str) -> str:
    if not GEMINI_API_KEY: 
        return "⚠️ Ошибка: API-ключ не задан в коде."
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    system_instruction = (
        "Ты — профессиональный диетолог и шеф-повар. Твоя задача — составить рецепт для мамы пользователя. "
        "У неё строгая диета (мягкая, нежирная пища, без обжарки, минимум соли, без острого и без сахара — аналог стола №5). "
        "Готовить можно ИСКЛЮЧИТЕЛЬНО в мультиварке Xiaomi Mijia, используя только два режима: 'Soup' и 'Steam'. "
        "Из предложенных ингредиентов выбери подходящие и составь ОДИН пошаговый рецепт. Отвечай на русском языке."
    )
    
    payload = {"contents": [{"parts": [{"text": f"{system_instruction}\n\nПродукты: {ingredients}"}]}]}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['candidates'][0]['content']['parts'][0]['text']
                else:
                    error_data = await response.text()
                    return f"❌ Ошибка сервера Google (Код: {response.status}). Ответ: {error_data[:100]}"
    except Exception as e: 
        return f"❌ Не удалось связаться с AI из-за сетевой ошибки: {str(e)}"

@dp.message(F.text == "🥘 Что приготовить из холодильника?")
async def ingredients_request(message: types.Message, state: FSMContext):
    if message.from_user.id not in [MOM_ID, ADMIN_ID]: return
    await state.set_state(ChatStates.waiting_for_ingredients)
    await message.answer("🥦 Напиши, какие продукты сейчас есть в холодильнике?")

@dp.message(ChatStates.waiting_for_ingredients)
async def generate_and_send_recipe(message: types.Message, state: FSMContext):
    # Отправляем сообщение "Минутку..."
    waiting_msg = await message.answer("⏳ Минутку, подбираю полезный рецепт для мультиварки...")
    
    # Запрашиваем рецепт у ИИ
    recipe = await ask_gemini_recipe(message.text)
    
    # СНАЧАЛА удаляем "Минутку...", чтобы чат выглядел красиво
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=waiting_msg.message_id)
    except:
        pass
        
    # ТЕПЕРЬ выводим сам рецепт
    await message.answer(recipe, parse_mode="Markdown")
    await state.clear()

# ==========================================
# ЛИНИЯ СВЯЗИ (МАМА - СЫН)
# ==========================================
@dp.message(F.text == "❓ Задать вопрос сыну")
async def start_asking(message: types.Message, state: FSMContext):
    if message.from_user.id not in [MOM_ID, ADMIN_ID]: return
    await state.set_state(ChatStates.waiting_for_mom_question)
    await message.answer("✍️ Напиши вопрос, я сразу передам его сыну.")

@dp.message(ChatStates.waiting_for_mom_question)
async def forward_question_to_son(message: types.Message, state: FSMContext):
    await bot.forward_message(chat_id=ADMIN_ID, from_chat_id=message.chat.id, message_id=message.message_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✍️ Ответить маме", callback_data="reply_to_mom")]])
    await bot.send_message(chat_id=ADMIN_ID, text="👆 Это вопрос от мамы.", reply_markup=keyboard)
    await message.answer("✅ Вопрос отправлен. Ждем ответа.")
    await state.clear()

@dp.callback_query(F.data == "reply_to_mom")
async def admin_reply_handler(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(ChatStates.waiting_for_son_reply)
    await callback.message.edit_text("✍️ Напишите ваш ответ:")
    await callback.answer()

@dp.message(ChatStates.waiting_for_son_reply)
async def send_reply_to_mom(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await bot.send_message(chat_id=MOM_ID, text="📩 Сообщение от сына:")
    await bot.copy_message(chat_id=MOM_ID, from_chat_id=message.chat.id, message_id=message.message_id)
    await message.answer("✅ Ответ доставлен маме.")
    await state.clear()

# ==========================================
# СЕРВЕР И ЗАПУСК
# ==========================================
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    if message.from_user.id in [MOM_ID, ADMIN_ID]:
        await message.answer("Бот готов к заботе о маме!", reply_markup=get_mom_menu())
    else:
        await message.answer("Бот запущен!")

async def handle(request): return web.Response(text="Bot is running")

async def main():
    # 1. Ежеминутная проверка будильников для лекарств из базы данных
    scheduler.add_job(check_and_send_pills, 'cron', second=0)
    
    # 2. Расписание 6-разового питания (ВРЕМЯ ТАШКЕНТСКОЕ)
    scheduler.add_job(send_food_reminder, 'cron', hour=8, minute=0, args=["Завтрак 🍳"])
    scheduler.add_job(send_food_reminder, 'cron', hour=11, minute=0, args=["Второй завтрак 🍏"])
    scheduler.add_job(send_food_reminder, 'cron', hour=13, minute=0, args=["Обед 🍲"])
    scheduler.add_job(send_food_reminder, 'cron', hour=16, minute=0, args=["Полдник 🥛"])
    scheduler.add_job(send_food_reminder, 'cron', hour=19, minute=0, args=["Ужин 🐠"])
    scheduler.add_job(send_food_reminder, 'cron', hour=21, minute=0, args=["Легкий перекус перед сном 🧊"])
    
    scheduler.start()
    
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
