import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from backend.config import settings

logging.basicConfig(level=logging.INFO)
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    web_app_url = "https://your-frontend-url.onrender.com" # Frontend URL ni shu yerga yozasiz
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="⚔️ BEK ARENA'NI BOSHLASH",
                    web_app=types.WebAppInfo(url=web_app_url)
                )
            ]
        ]
    )
    await message.answer(
        "🎖 **Xush kelibsiz, Komandir!**\n\n"
        "BEK ARENA: WAR — Telegram ichidagi eng ilg‘or harbiy strategiya o‘yini.\n"
        "Bazangizni quring, qo‘shin to‘plang va dushmanlarni tor-mor eting!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
