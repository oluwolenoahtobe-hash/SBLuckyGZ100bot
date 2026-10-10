import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command

# --- Configuration ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# --- Bot & Dispatcher ---
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()
router = Router()


# --- Mock AI Service ---
async def analyze_product_image(image_url: str) -> dict:
    await asyncio.sleep(1)
    return {
        "ingredients": "Aqua, Glycerin, Niacinamide, Zinc PCA.",
        "origin": "Made in South Korea. Distributed by GlowLab Inc.",
        "category": "Skincare / Facial Serum",
        "package": "30ml amber glass bottle with dropper.",
        "similar": "1. The Ordinary Niacinamide 10% + Zinc 1%\n2. Paula's Choice 10% Niacinamide Booster",
        "notes": "User noted: Purchased from official store. Expiry 2027.",
    }


# --- Handlers ---
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    logger.info(f"/start from {message.from_user.id}")
    await message.answer(
        "👋 <b>Welcome to SBLuckyGZ Product ID Bot!</b>\n\n"
        "Send me a photo of a product and I'll identify it.\n\n"
        "<b>Features:</b>\n"
        "1. Ingredients\n"
        "2. Country/Region\n"
        "3. Product Category\n"
        "4. Package Info\n"
        "5. Similar Products\n"
        "6. User Notes"
    )


@router.message(F.photo)
async def handle_product_photo(message: types.Message):
    processing_msg = await message.answer("🔍 Analyzing product image... Please wait.")
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

        data = await analyze_product_image(file_url)

        response_text = (
            "📦 <b>Product Analysis Complete</b>\n\n"
            f"<b>1. Ingredients:</b>\n{data['ingredients']}\n\n"
            f"<b>2. Country/Region:</b>\n{data['origin']}\n\n"
            f"<b>3. Product Category:</b>\n{data['category']}\n\n"
            f"<b>4. Package Information:</b>\n{data['package']}\n\n"
            f"<b>5. Similar Products:</b>\n{data['similar']}\n\n"
            f"<b>6. User Notes:</b>\n{data['notes']}"
        )
        await processing_msg.edit_text(response_text)

    except Exception as e:
        logger.error(f"Error processing photo: {e}", exc_info=True)
        await processing_msg.edit_text(
            "❌ Sorry, I couldn't identify this product. Please try a clearer photo."
        )


@router.message(F.text & ~F.text.startswith("/"))
async def handle_notes(message: types.Message):
    await message.answer(
        "📝 <b>Notes Feature:</b> Your message has been logged. (Coming soon.)"
    )


# --- Entrypoint ---
async def main():
    dp.include_router(router)

    # IMPORTANT: delete any stale webhook so polling can receive updates
    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.get_me()
    logger.info(f"🤖 Bot started: @{me.username} ({me.id})")
    logger.info("🔄 Starting polling mode...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
