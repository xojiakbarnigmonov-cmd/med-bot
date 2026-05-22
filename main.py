import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = os.getenv("BOT_TOKEN")

# ==========================================
# ВАШИ НАСТРОЙКИ (Замените цифры на ваши ID)
# ==========================================
ADMIN_ID = 269215305  # Ваш ID
MOM_ID = 5599753365    # ID мамы (Для теста можете временно вписать сюда свой ID, чтобы увидеть, как это выглядит для нее)

bot = Bot(token=TOKEN)
dp = Dispatcher()
# Планировщик в часовом поясе Ташкента
scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

# ==========================================
# ЛОГИКА НАПОМИНАНИЙ О ЛЕКАРСТВАХ
# ==========================================

async def send_pill_reminder():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Приняла", callback_data="took_pill_morning")]
    ])
    try:
        await bot.send_message(
            chat_id=MOM_ID, 
            text="💊 Мама, доброе утро! Пора выпить утренние лекарства.", 
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Ошибка отправки маме: {e}")

@dp.callback_query(F.data == "took_pill_morning")
async def pill_taken_handler(callback: types.CallbackQuery):
    # Меняем сообщение мамы
    await callback.message.edit_text("💊 Утренние лекарства — ✅ Принято! Молодец, мамуля ❤️")
    
    # Отправляем уведомление вам
    await bot.send_message(
        chat_id=ADMIN_ID, 
        text="✅ Мама только что приняла утренние лекарства!"
    )
    await callback.answer()

# ==========================================
# КОМАНДЫ БОТА
# ==========================================

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Бот запущен! Ждем времени приема лекарств.")

# Команда для тестирования прямо сейчас
@dp.message(Command("test"))
async def test_reminder(message: types.Message):
    await message.answer("Запускаю тестовое напоминание...")
    await send_pill_reminder()

# ==========================================
# ВЕБ-СЕРВЕР (чтобы бот не падал на Render)
# ==========================================
async def handle(request):
    return web.Response(text="Bot is running")

async def main():
    # Расписание (каждый день в 09:00 утра)
    scheduler.add_job(send_pill_reminder, 'cron', hour=9, minute=0)
    scheduler.start()
    
    # Запуск веб-сервера
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
