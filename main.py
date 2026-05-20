import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Этот кусок кода создает "сайт", который ничего не делает. 
# Render увидит, что порт открыт, и успокоится.
async def health_check(request):
    return web.Response(text="Bot is alive!")

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Бот успешно запущен и работает!")

async def start_bot():
    await dp.start_polling(bot)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    # Берем порт, который дает Render
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Сервер слушает порт {port}")

async def main():
    await asyncio.gather(start_web_server(), start_bot())

if __name__ == "__main__":
    asyncio.run(main())
