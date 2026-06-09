import logging

logger = logging.getLogger(__name__)


async def send_long_message(channel, text: str, limit: int = 1900):
    """Kirim pesan panjang dalam beberapa chunk agar tidak melebihi batas Discord 2000 char."""
    if len(text) <= limit:
        await channel.send(text)
        return

    parts = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit:
            if current:
                parts.append(current)
            current = line
        else:
            current = (current + "\n" + line) if current else line

    if current:
        parts.append(current)

    for part in parts:
        await channel.send(part)


async def handle_pengeluaran_request(msg, user_prompt: str, uang_kas_service, UANG_KAS_AVAILABLE: bool) -> bool:
    """
    Handler pengeluaran kelas. Menampilkan semua baris dari sheet 'Pengeluaran'
    ketika user bertanya tentang detail pengeluaran/pembelian kelas.
    Diprioritaskan sebelum handle_uang_kas_request agar tidak ditangkap oleh
    intent "pengeluaran" generik di handler kas.
    """
    prompt_lower = user_prompt.lower()

    pengeluaran_intents = [
        "pengeluaran kelas", "dipakai apa", "dipakai buat apa",
        "daftar pengeluaran", "list pengeluaran", "pengeluaran apa saja",
        "pengeluaran apa", "beli apa saja", "beli apa", "pembelian kelas",
        "uang dipakai", "kas dipakai", "pengeluaran kas kelas",
        "dibeliin apa", "dibelikan apa", "kas buat apa",
    ]
    if not any(intent in prompt_lower for intent in pengeluaran_intents):
        return False

    if not UANG_KAS_AVAILABLE or uang_kas_service is None:
        await msg.channel.send("⚠️ Fitur uang kas tidak tersedia.")
        return True

    if not uang_kas_service._initialized:
        await uang_kas_service.initialize()
        if not uang_kas_service._initialized:
            await msg.channel.send("⚠️ Fitur uang kas belum terkonfigurasi.")
            return True

    await msg.channel.typing()

    try:
        items = await uang_kas_service.get_pengeluaran_list()
        response = uang_kas_service.format_pengeluaran_list_response(items)
        await send_long_message(msg.channel, response)
        return True
    except Exception as e:
        logger.error(f"❌ Error handling pengeluaran request: {e}")
        await msg.channel.send("❌ Terjadi kesalahan saat mengambil data pengeluaran.")
        return True