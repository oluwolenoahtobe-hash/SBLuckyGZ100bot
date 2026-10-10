import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# --- Configuration ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")
WEBHOOK_PATH = "/webhook"

# Fail fast if the token is missing
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# --- Initialize Bot (FIXED for aiogram 3.7.0+) ---
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()
router = Router()


# --- Mock Service Layer (Replace with your AI API) ---
async def analyze_product_image(image_url: str) -> dict:
    """
    Replace this with a real Vision AI call (e.g., OpenAI GPT-4o, Qwen3-VL).
    """
    await asyncio.sleep(1)
    return {
        "ingredients": "Aqua, Glycerin, Niacinamide, Zinc PCA.",
        "origin": "Made in South Korea. Distributed by GlowLab Inc.",
        "category": "Skincare / Facial Serum",
        "package": "30ml amber glass bottle with dropper. Recyclable cardboard box.",
        "similar": "1. The Ordinary Niacinamide 10% + Zinc 1%\n2. Paula's Choice 10% Niacinamide Booster",
        "notes": "User noted: Purchased from official brand store. Expiry 2027.",
    }


# --- Handlers ---
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "👋 <b>Welcome to SBLuckyGZ Product ID Bot!</b>\n\n"
        "I can identify products from photos. Just send me a clear picture of the item.\n\n"
        "<b>Features:</b>\n"
        "1. Ingredients\n"
        "2. Country/Region\n"
        "3. Product Category\n"
        "4. Package Info\n"
        "5. Similar Products\n"
        "6. User Notes"
    )
    await message.answer(welcome_text)


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
        "📝 <b>Notes Feature:</b>\n"
        "You can add custom notes to any product. "
        "This function is currently in development, but your message has been logged."
    )


# --- Webhook / Railway Setup ---
async def on_startup(bot: Bot):
    if WEBHOOK_BASE_URL:
        webhook_url = f"{WEBHOOK_BASE_URL.rstrip('/')}{WEBHOOK_PATH}"
        await bot.set_webhook(webhook_url, drop_pending_updates=True)
        logger.info(f"✅ Webhook set to {webhook_url}")
    else:
        logger.warning(
            "⚠️ WEBHOOK_BASE_URL not set. The bot will not receive updates. "
            "Add it in Railway Variables and redeploy."
        )


async def on_shutdown(bot: Bot):
    try:
        await bot.delete_webhook()
        logger.info("Webhook deleted.")
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")


def main():
    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    # Health check endpoint for Railway
    async def health(request):
        return web.Response(text="OK")

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    # Register webhook handler
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    port = int(os.getenv("PORT", 8080))
    logger.info(f"🚀 Starting server on 0.0.0.0:{port}")
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
