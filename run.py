import os
import time as py_time
import logging
from dotenv import load_dotenv
import discord

# Setup logging first
from src.logger import setup_logging
setup_logging()

logger = logging.getLogger(__name__)

print("🚀 Starting Techfour Bot")

# Start health server
from src.health_server import start_health_server
start_health_server()

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GENERAL_CHANNEL_ID = int(os.getenv("GENERAL_CHANNEL_ID", 0))

# Token validation
if not DISCORD_TOKEN:
    logger.error("❌ DISCORD_TOKEN not found")
    print("❌ DISCORD_TOKEN tidak ditemukan!")
    try:
        while True:
            py_time.sleep(60)
    except KeyboardInterrupt:
        exit(0)
else:
    if not DISCORD_TOKEN.startswith('MT') or len(DISCORD_TOKEN) < 50:
        logger.error(f"❌ Invalid DISCORD_TOKEN format")
        print("❌ Format token tidak valid!")
        try:
            while True:
                py_time.sleep(60)
        except KeyboardInterrupt:
            exit(0)
    else:
        print(f"✅ Token found, length: {len(DISCORD_TOKEN)} characters")

# Import services
try:
    from services.ai_bot_service import ai_bot_service
except ImportError:
    class MockAIBotService:
        async def get_response(self, prompt, user_id, image_bytes=None):
            return f"AI Response untuk: {prompt}"
    ai_bot_service = MockAIBotService()

try:
    from services.uang_kas_service import uang_kas_service
    UANG_KAS_AVAILABLE = True
except ImportError:
    UANG_KAS_AVAILABLE = False
    uang_kas_service = None
    print("⚠️ uang_kas_service tidak tersedia")

# Setup bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.presences = True

# Create bot instance
from src.bot import create_bot, rate_limiter, activity_tracker, is_admin
bot = create_bot(intents)

# Create background tasks for jadwal reminders
from src.jadwal_kuliah import create_background_tasks
create_background_tasks(bot, GENERAL_CHANNEL_ID)

# Import message handler
from src.message_handler import on_message

# Register the on_message event
@bot.event
async def on_message_event(msg):
    await on_message(
        msg=msg,
        bot_ref=bot,
        ai_service=ai_bot_service,
        rate_limiter=rate_limiter,
        activity_tracker=activity_tracker,
        is_admin_func=is_admin,
        DISCORD_TOKEN=DISCORD_TOKEN,
        uang_kas_service=uang_kas_service,
        UANG_KAS_AVAILABLE=UANG_KAS_AVAILABLE,
        GENERAL_CHANNEL_ID=GENERAL_CHANNEL_ID
    )

bot.on_message(on_message_event)

# Run bot
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ No DISCORD_TOKEN, running health server only")
        try:
            while True:
                py_time.sleep(60)
        except KeyboardInterrupt:
            print("Server stopped")
    else:
        print("🤖 Starting Discord bot...")
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                bot.run(DISCORD_TOKEN)
            except discord.LoginFailure:
                print("❌ Login failed: Invalid token!")
                break
            except discord.ConnectionClosed as e:
                print(f"❌ Connection closed: {e}. Retry {retry_count + 1}/{max_retries}")
                retry_count += 1
                py_time.sleep(5)
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                logger.error(f"Unexpected error: {e}")
                break
            else:
                break

        if retry_count >= max_retries:
            print("❌ Failed to connect after retries")