import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- Configuration ---
# Railway will provide these environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Railway provides a public domain automatically. 
# You must set this to your Railway URL (e.g., https://your-app.up.railway.app)
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL") 
WEBHOOK_PATH = "/webhook"

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Bot and Dispatcher
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
router = Router()

# --- Mock Service Layer (Replace with actual AI API) ---
async def analyze_product_image(image_url: str) -> dict:
    """
    This is where you connect your Vision AI (e.g., OpenAI GPT-4o, Qwen3-VL).
    It should return a structured dictionary with the product data.
    """
    # Simulated delay and response for now
    await asyncio.sleep(1) 
    return {
        "ingredients": "Aqua, Glycerin, Niacinamide, Zinc PCA.",
        "origin": "Made in South Korea. Distributed by GlowLab Inc.",
        "category": "Skincare / Facial Serum",
        "package": "30ml amber glass bottle with dropper. Outer box is recyclable cardboard.",
        "similar": "1. The Ordinary Niacinamide 10% + Zinc 1%\n2. Paula's Choice 10% Niacinamide Booster",
        "notes": "User noted: Purchased from official brand store. Expiry 2027."
    }

# --- Handlers ---
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        f"👋 <b>Welcome to SBLuckyGZ Product ID Bot!</b>\n\n"
        f"I can identify products from photos. Just send me a clear picture of the item.\n\n"
        f"<b>Features:</b>\n"
        f"1. Ingredients\n"
        f"2. Country/Region\n"
        f"3. Product Category\n"
        f"4. Package Info\n"
        f"5. Similar Products\n"
        f"6. User Notes"
    )
    await message.answer(welcome_text)

@router.message(F.photo)
async def handle_product_photo(message: types.Message):
    # Inform user we are processing
    processing_msg = await message.answer("🔍 Analyzing product image... Please wait.")
    
    try:
        # 1. Get the largest photo size available
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        
        # 2. Construct the Telegram CDN URL for the image
        # Note: In a real app, you might want to download the bytes and send to API
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        
        # 3. Call your AI Service
        data = await analyze_product_image(file_url)
        
        # 4. Format the response
        response_text = (
            f"📦 <b>Product Analysis Complete</b>\n\n"
            f"<b>1. Ingredients:</b>\n{data['ingredients']}\n\n"
            f"<b>2. Country/Region:</b>\n{data['origin']}\n\n"
            f"<b>3. Product Category:</b>\n{data['category']}\n\n"
            f"<b>4. Package Information:</b>\n{data['package']}\n\n"
            f"<b>5. Similar Products:</b>\n{data['similar']}\n\n"
            f"<b>6. User Notes:</b>\n{data['notes']}"
        )
        
        await processing_msg.edit_text(response_text)
        
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await processing_msg.edit_text("❌ Sorry, I couldn't identify this product. Please try a clearer photo.")

@router.message(F.text & ~F.text.startswith('/'))
async def handle_notes(message: types.Message):
    # Handle user-created notes (Feature 6)
    await message.answer(
        "📝 <b>Notes Feature:</b>\n"
        "You can add custom notes to any product. "
        "This function is currently in development, but your message has been logged."
    )

# --- Railway / Webhook Setup ---
def setup_webhook_routes(app: web.Application):
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

async def on_startup(bot: Bot):
    # Set the webhook when the app starts
    if WEBHOOK_BASE_URL:
        webhook_url = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}"
        await bot.set_webhook(webhook_url, drop_pending_updates=True)
        logger.info(f"Webhook set to {webhook_url}")
    else:
        logger.error("WEBHOOK_BASE_URL not set. Webhook cannot be configured.")

async def on_shutdown(bot: Bot):
    # Clean up webhook on shutdown
    await bot.delete_webhook()

def main():
    # Include the router in the dispatcher
    dp.include_router(router)
    
    # Register lifecycle events
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Create aiohttp app
    app = web.Application()
    setup_webhook_routes(app)
    
    # Run the app
    # Railway provides a PORT environment variable
    port = int(os.getenv("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
