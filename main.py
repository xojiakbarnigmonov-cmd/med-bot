import asyncio
import gspread
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import os

# Ваш токен от BotFather
TOKEN = os.getenv("BOT_TOKEN") 
# Ссылка на вашу таблицу (вставьте свою)
SHEET_URL = "ВАША_ССЫЛКА_НА_ТАБЛИЦУ"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Подключение к таблице
gc = gspread.service_account_from_dict(os.environ.get("GOOGLE_CREDENTIALS")) # Это мы настроим на хостинге
sheet = gc.open_by_url(SHEET_URL).worksheet("Meds")

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Привет! Бот готов к работе с таблицей.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
