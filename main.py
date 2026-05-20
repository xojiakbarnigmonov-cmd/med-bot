import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Обработчик, который говорит Render: "Я тут, я живой!"
async def handle(request):
    return web.Response(text="Bot is running")

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Бот успешно запущен и работает!")

# Запуск бота и веб-сервера одновременно
async def main():
    # Запускаем веб-сервер на порту, который выдал Render
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
