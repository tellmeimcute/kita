import logging

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from database.db_manager import DatabaseManager

from middlewares.session import SessionMiddleware
from middlewares.user import UserMiddleware

from handlers.suggest import router as suggest_router
from config import config

logging.basicConfig(level=logging.INFO)

db = DatabaseManager()
dp = Dispatcher()
dp.include_router(suggest_router)

bot = Bot(config.TG_TOKEN.get_secret_value(), default=DefaultBotProperties())

session_middleware = SessionMiddleware(db.session_maker)
user_middleware = UserMiddleware()

dp.message.middleware(session_middleware)
dp.message.middleware(user_middleware)

dp.callback_query.middleware(session_middleware)
dp.callback_query.middleware(user_middleware)


async def main():
    # не использовать в проде
    await db.start_dev()

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Закрываюсь...")
