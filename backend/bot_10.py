import asyncio
import logging
from datetime import datetime
from io import BytesIO

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile

from backend.backup_service import export_data, import_data
from backend.config import settings

logging.basicConfig(level=logging.INFO)
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

MAX_BACKUP_SIZE = 20 * 1024 * 1024  # Telegram bot yuklab olish limiti


def is_admin(message: types.Message) -> bool:
    return message.from_user is not None and message.from_user.id in settings.ADMIN_IDS


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
    await message.answer(
        "🎖 <b>Xush kelibsiz, Komandir!</b>\n\n"
        "BEK ARENA: WAR — Telegram ichidagi eng ilg‘or harbiy strategiya o‘yini.\n"
        "Bazangizni quring, qo‘shin to‘plang va dushmanlarni tor-mor eting!",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@dp.message(Command("myid"))
async def cmd_myid(message: types.Message):
    await message.answer(
        f"Sizning Telegram ID: <code>{message.from_user.id}</code>", parse_mode="HTML"
    )


async def send_backup(message: types.Message, caption: str):
    raw = await asyncio.to_thread(export_data)
    filename = f"bek_arena_backup_{datetime.utcnow():%Y%m%d_%H%M}.json"
    await message.answer_document(BufferedInputFile(raw, filename=filename), caption=caption)


@dp.message(Command("backup"))
async def cmd_backup(message: types.Message):
    if not is_admin(message):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun.")
        return
    try:
        await send_backup(message, "💾 Backup tayyor. Tiklash uchun shu faylni /restore izohi bilan yuboring.")
    except Exception:
        logging.exception("Backup xatosi")
        await message.answer("❌ Backup yaratishda xatolik bo'ldi.")


# Fayl izohida /restore yozib yuborilsa yoki faylga reply qilib /restore yozilsa ishlaydi
@dp.message(Command("restore"))
@dp.message(F.document, F.caption.startswith("/restore"))
async def cmd_restore(message: types.Message):
    if not is_admin(message):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun.")
        return

    doc = message.document
    if doc is None and message.reply_to_message is not None:
        doc = message.reply_to_message.document

    if doc is None:
        await message.answer(
            "Backup faylini (.json) yuboring va izohiga /restore deb yozing,\n"
            "yoki fayl ostiga reply qilib /restore yozing."
        )
        return

    if not (doc.file_name or "").lower().endswith(".json"):
        await message.answer("❌ Faqat .json backup fayli qabul qilinadi.")
        return
    if doc.file_size and doc.file_size > MAX_BACKUP_SIZE:
        await message.answer("❌ Fayl juda katta.")
        return

    try:
        # Xavfsizlik uchun: tiklashdan oldin hozirgi holatni ham yuboramiz
        await send_backup(message, "🛟 Tiklashdan oldingi holat (kerak bo'lsa shuni qaytarasiz).")

        buf = BytesIO()
        await bot.download(doc, destination=buf)
        counts = await asyncio.to_thread(import_data, buf.getvalue())
    except ValueError as e:  # noto'g'ri fayl/format (JSONDecodeError ham shu yerga kiradi)
        await message.answer(f"❌ Fayl yaroqsiz: {e}\nBaza o'zgarmadi.")
        return
    except Exception:
        logging.exception("Restore xatosi")
        await message.answer("❌ Tiklashda xatolik bo'ldi. Baza o'zgarmadi.")
        return

    await message.answer(
        "✅ Baza tiklandi!\n"
        f"👤 Foydalanuvchilar: {counts['users']}\n"
        f"🏰 Bazalar: {counts['bases']}\n"
        f"🏗 Binolar: {counts['buildings']}"
    )


async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
