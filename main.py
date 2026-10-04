import os
import asyncio
from handlers import router
from dotenv import load_dotenv
from connection import init_tables
from aiogram import Bot, Dispatcher
from callbacks import router as callback_router


load_dotenv()


bot = Bot(os.getenv("BOT_TOKEN"))
dp = Dispatcher()

async def main():
    await init_tables()
    dp.include_router(router)
    dp.include_router(callback_router)
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())