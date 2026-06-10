import logging
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


# Toxic word filter
TOXIC_WORDS = [
    "kontol", "memek", "bangsat", "ngentod", "jembut", "anjing",
    "brengsek", "tai", "tolol", "babi", "goblok", "ngewe"
]


async def handle_message(msg: discord.Message, bot_ref, ai_service, rate_limiter,
                         activity_tracker, is_admin_func, DISCORD_TOKEN: str,
                         uang_kas_service, UANG_KAS_AVAILABLE: bool,
                         GENERAL_CHANNEL_ID: int):
    """
    Handle incoming messages.

    This is the main message handler that processes:
    - Toxic word filtering
    - Bot mentions (OCR, jadwal, uang kas, pengeluaran, AI)
    - Commands
    """
    from src.jadwal_kuliah import handle_jadwal_request
    from src.uang_kas import handle_uang_kas_request
    from src.pengeluaran import handle_pengeluaran_request
    from src.ocr import handle_ocr_attachment

    if msg.author == bot_ref.user:
        return

    activity_tracker.update_activity(msg.author.id)

    # Toxic word filter
    if any(word in msg.content.lower() for word in TOXIC_WORDS):
        try:
            await msg.delete()
            await msg.channel.send(f"{msg.author.mention} jaga bahasanya ya 🙏")
        except Exception as e:
            logger.error(f"❌ Delete message error: {e}")
        return

    # Handler untuk mention bot
    if bot_ref.user.mentioned_in(msg) and not msg.mention_everyone:
        user_prompt = msg.content.replace(f"<@{bot_ref.user.id}>", "").replace(f"<@!{bot_ref.user.id}>", "").strip()

        # Handler OCR - priority
        if msg.attachments:
            for attachment in msg.attachments:
                if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".pdf")):
                    await handle_ocr_attachment(attachment, msg.author.id, msg.channel, ai_service, DISCORD_TOKEN)
                    return

        # Priority 2: Jadwal
        if await handle_jadwal_request(msg, user_prompt, bot_ref, GENERAL_CHANNEL_ID):
            return

        # Priority 3: Pengeluaran Kelas
        if await handle_pengeluaran_request(msg, user_prompt, uang_kas_service, UANG_KAS_AVAILABLE):
            return

        # Priority 4: Uang Kas
        if await handle_uang_kas_request(msg, user_prompt, uang_kas_service, UANG_KAS_AVAILABLE):
            return

        # Priority 5: AI
        if not user_prompt:
            await msg.channel.send("Halo! Ada yang bisa kubantu?")
            return

        admin = is_admin_func(msg.author)
        can_use, error_msg = await rate_limiter.can_use_ai(msg.author.id, admin)

        if not can_use:
            await msg.channel.send(error_msg)
            return

        await msg.channel.typing()
        await rate_limiter.record(msg.author.id)

        reply = await ai_service.get_response(user_prompt, msg.author.id, image_bytes=None)
        await msg.channel.send(reply[:2000])
        return

    await bot_ref.process_commands(msg)