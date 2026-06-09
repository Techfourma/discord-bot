import logging
import aiohttp
from discord.ext import commands

logger = logging.getLogger(__name__)


async def handle_ocr_attachment(attachment, user_id: int, channel, ai_service, discord_token: str):
    """
    Handle OCR for image attachments.

    Args:
        attachment: Discord attachment object
        user_id: ID of the user who sent the image
        channel: Discord channel to send responses
        ai_service: AI service instance for OCR processing
        discord_token: Discord bot token for downloading images
    """
    try:
        if attachment.size > 5_000_000:
            await channel.send("❌ File terlalu besar (max 5MB).")
            return

        headers = {"Authorization": f"Bot {discord_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url, headers=headers, timeout=15) as resp:
                if resp.status != 200:
                    await channel.send(f"❌ Gagal download gambar. Status: {resp.status}")
                    return
                image_bytes = await resp.read()

        await channel.typing()
        ocr_result = await ai_service.get_response(
            "Tolong ekstrak semua teks yang terlihat di gambar ini.",
            user_id,
            image_bytes=image_bytes
        )
        await channel.send(f"📄 **Hasil OCR:**\n{ocr_result[:1900]}")
        logger.info("✅ OCR completed")

    except Exception as e:
        logger.error(f"❌ OCR error: {e}")
        await channel.send("❌ Gagal memproses gambar.")