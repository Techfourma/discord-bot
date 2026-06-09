import logging
import re
from datetime import datetime
from typing import Optional

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


async def handle_uang_kas_request(msg, user_prompt: str, uang_kas_service, UANG_KAS_AVAILABLE: bool) -> bool:
    """
    Handler uang kas. Skenario:
    1. Nama spesifik  → format_single_student_response
    2. "nunggak"      → format_nunggak_summary_response
    3. Minggu ini/lalu → format_unpaid_weekly_response
    4. Saldo/pengeluaran/pemasukan
    5. Default (belum bayar semua) → format_unpaid_detailed_response
    Semua hasil hanya menghitung tanggal yang SUDAH LEWAT dari hari ini.
    """
    prompt_lower = user_prompt.lower()

    uang_kas_intents = [
        "uang kas", "kas", "belum bayar", "siapa yang belum",
        "tracking belum", "jumlah uang kas", "saldo kas", "sisa kas",
        "pengeluaran kas", "total pengeluaran", "pemasukan kas",
        "nunggak", "tunggak", "bayar kas", "sudah bayar", "udah bayar",
        "cek kas", "apakah bayar",
    ]
    if not any(intent in prompt_lower for intent in uang_kas_intents):
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
        # Check specific name
        from src.parser import extract_student_name
        detected_name = extract_student_name(user_prompt)

        if detected_name:
            student = await uang_kas_service.find_student_by_name(detected_name)
            if student:
                response = uang_kas_service.format_single_student_response(student)
            else:
                response = (
                    f"❌ Mahasiswa dengan nama '{detected_name}' tidak ditemukan.\n"
                    "Coba tulis nama lebih lengkap."
                )
            await send_long_message(msg.channel, response)
            return True

        # Rekap tunggakan
        if any(kw in prompt_lower for kw in ["nunggak", "tunggak", "rekap"]):
            detailed_list = await uang_kas_service.get_all_unpaid_detailed()
            response = uang_kas_service.format_nunggak_summary_response(detailed_list)
            await send_long_message(msg.channel, response)
            return True

        # Weekly unpaid
        if "minggu ini" in prompt_lower or "minggu" in prompt_lower:
            today = datetime.now()
            if today.weekday() == 0:
                unpaid_list = await uang_kas_service.get_unpaid_last_week()
                week_label = "MINGGU LALU"
            else:
                unpaid_list = await uang_kas_service.get_unpaid_this_week()
                week_label = "MINGGU INI"
            response = uang_kas_service.format_unpaid_weekly_response(unpaid_list, week_label)
            await send_long_message(msg.channel, response)
            return True

        # Cashflow summary
        if any(kw in prompt_lower for kw in ["saldo", "sisa", "berapa jumlah"]):
            if "pengeluaran" in prompt_lower:
                val = await uang_kas_service.get_total_expenditure()
                await msg.channel.send(uang_kas_service.format_expenditure_response(val))
            elif "pemasukan" in prompt_lower:
                val = await uang_kas_service.get_total_income()
                await msg.channel.send(uang_kas_service.format_income_response(val))
            else:
                balance = await uang_kas_service.get_current_balance()
                await msg.channel.send(uang_kas_service.format_balance_response(balance))
            return True

        if "pengeluaran" in prompt_lower:
            val = await uang_kas_service.get_total_expenditure()
            await msg.channel.send(uang_kas_service.format_expenditure_response(val))
            return True

        if "pemasukan" in prompt_lower:
            val = await uang_kas_service.get_total_income()
            await msg.channel.send(uang_kas_service.format_income_response(val))
            return True

        # Default: list semua yang belum bayar
        detailed_list = await uang_kas_service.get_all_unpaid_detailed()
        response = uang_kas_service.format_unpaid_detailed_response(detailed_list)
        await send_long_message(msg.channel, response)
        return True

    except Exception as e:
        logger.error(f"❌ Error handling uang kas request: {e}")
        await msg.channel.send("❌ Terjadi kesalahan saat mengambil data kas.")
        return True