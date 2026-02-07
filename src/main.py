import logging

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from database import DatabaseManager
from middlewares import SessionMiddleware, UserMiddleware
from handlers import handlers_router

from config import config

logging.basicConfig(level=logging.INFO)

db = DatabaseManager()
dp = Dispatcher(config=config)
dp.include_router(handlers_router)

bot = Bot(config.TG_TOKEN.get_secret_value(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))

session_middleware = SessionMiddleware(db.session_maker)
user_middleware = UserMiddleware()

dp.message.middleware(session_middleware)
dp.message.middleware(user_middleware)

#dp.callback_query.middleware(session_middleware)
#dp.callback_query.middleware(user_middleware)


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
