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
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="⚔️ BEK ARENA'NI BOSHLASH",
                    web_app=types.WebAppInfo(url=settings.WEBAPP_URL),
                )
            ]
        ]
    )
    # Telegram'ning eski "Markdown" rejimida ** ishlamaydi, shuning uchun HTML ishlatildi
    await message.answer(
        "🎖 <b>Xush kelibsiz, Komandir!</b>\n\n"
        "BEK ARENA: WAR — Telegram ichidagi eng ilg‘or harbiy strategiya o‘yini.\n"
        "Bazangizni quring, qo‘shin to‘plang va dushmanlarni tor-mor eting!",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
