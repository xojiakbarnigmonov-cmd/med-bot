import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Получаем токен из настроек Render
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Бот успешно запущен! Я на связи.")

async def main():
    print("Бот успешно запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
