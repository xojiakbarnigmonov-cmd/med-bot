import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# ВАЖНО: Мы будем хранить настройки в переменных окружения (на хостинге)
import os

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Привет! Я ваш медицинский помощник. Бот запущен!")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
