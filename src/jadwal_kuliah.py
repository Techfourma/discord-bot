import logging
import re
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Dict, List, Optional
from discord.ext import tasks

logger = logging.getLogger(__name__)

WIB = dt_timezone(timedelta(hours=7))


def format_jadwal_entry(jadwal: Dict) -> str:
    """Format a single jadwal entry for display."""
    header = jadwal['header']
    content = jadwal['content']

    if header.lower().startswith('e-learning '):
        lines = content.split('\n')
        tatap_idx = next((i for i, l in enumerate(lines) if l.lower().startswith('tatap muka')), None)
        if tatap_idx is not None:
            e_learning_part = '\n'.join(lines[:tatap_idx]).strip()
            tatap_header = lines[tatap_idx].strip()
            tatap_content = '\n'.join(lines[tatap_idx+1:]).strip()
            result = f"__**{header}**__\n"
            if e_learning_part:
                result += f"`{e_learning_part}`\n"
            result += f"\n__**{tatap_header}**__\n"
            if tatap_content:
                result += f"`{tatap_content}`\n"
            return result
        else:
            return f"__**{header}**__\n`{content}`\n"
    elif header.lower().startswith('tatap muka'):
        return f"__**{header}**__\n`{content}`\n"
    else:
        return f"__**{header}**__\n`{content}`\n"


async def send_jadwal_list(channel, jadwal_list: List[Dict], header: str = ""):
    """Send a list of jadwal entries to the channel."""
    if not jadwal_list:
        await channel.send("📚 Tidak ada jadwal.")
        return

    msg = header
    for j in jadwal_list:
        entry = format_jadwal_entry(j)
        if len(msg) + len(entry) > 1900:
            await channel.send(msg)
            msg = ""
        msg += entry

    if msg:
        await channel.send(msg)


def parse_date_from_header(header: str):
    """Parse date from jadwal header."""
    try:
        month_map = {
            'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6,
            'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12,
            'january': 1, 'february': 2, 'march': 3, 'may': 5, 'june': 6,
            'july': 7, 'august': 8, 'october': 10, 'december': 12
        }

        # Pattern: "DD Month - DD Month YYYY"
        date_pattern = r'(\d{1,2})\s+([A-Za-z]+)\s*-\s*(\d{1,2})\s+([A-Za-z]+)'
        match = re.search(date_pattern, header)

        if match:
            start_day = int(match.group(1))
            start_month = month_map.get(match.group(2).lower(), 1)
            end_day = int(match.group(3))
            end_month = month_map.get(match.group(4).lower(), 1)

            year_match = re.search(r'(\d{4})', header)
            year = int(year_match.group(1)) if year_match else datetime.now(WIB).year

            start_date = datetime(year, start_month, start_day).date()
            end_date = datetime(year, end_month, end_day).date()

            return start_date, end_date

        # Pattern with day name: "DD Month - DayName"
        if " - " in header:
            parts = header.split(" - ", 1)
            start_match = re.search(r'(\d{1,2})\s+([A-Za-z]+)', parts[0])

            if start_match:
                start_day = int(start_match.group(1))
                start_month = month_map.get(start_match.group(2).lower(), 1)

                year_match = re.search(r'(\d{4})', header)
                year = int(year_match.group(1)) if year_match else datetime.now(WIB).year

                start_date = datetime(year, start_month, start_day).date()

                day_map = {'senin': 0, 'selasa': 1, 'rabu': 2, 'kamis': 3,
                          'jumat': 4, 'sabtu': 5, 'minggu': 6}
                end_day_name = parts[1].lower().strip()

                if end_day_name in day_map:
                    target_day = day_map[end_day_name]
                    days_diff = (target_day - start_date.weekday()) % 7
                    if days_diff == 0:
                        days_diff = 7
                    end_date = start_date + timedelta(days=days_diff)
                    return start_date, end_date

        return None, None

    except Exception as e:
        logger.error(f"❌ Date parsing error: {e}")
        return None, None


def parse_jadwal_file() -> List[Dict]:
    """Membaca dan memecah file jadwal, lalu mengeluarkan daftar entry."""
    try:
        with open('jadwal_kuliah.txt', 'r', encoding='utf-8') as file:
            content = file.read()

        sections = re.split(r'-{3,}\s*\n', content)
        jadwal_list = []

        for section in sections:
            section = section.strip()
            if not section:
                continue

            lines = section.split('\n', 1)
            if len(lines) < 2:
                continue

            header = lines[0].strip()
            content_text = lines[1].strip()

            start_date, end_date = parse_date_from_header(header)

            jadwal_list.append({
                "header": header,
                "content": content_text,
                "raw": section,
                "start_date": start_date,
                "end_date": end_date,
            })

        logger.info(f"✅ Parsed {len(jadwal_list)} jadwal")
        return jadwal_list

    except FileNotFoundError:
        logger.error("❌ jadwal_kuliah.txt not found")
        return [{"header": "Error", "content": "File tidak ditemukan", "raw": "Error", "start_date": None, "end_date": None}]
    except Exception as e:
        logger.error(f"❌ Error parsing jadwal: {e}")
        return [{"header": "Error", "content": f"Parse error: {e}", "raw": "Error", "start_date": None, "end_date": None}]


def get_jadwal_for_date(target_date) -> Optional[Dict]:
    """Get jadwal for a specific date."""
    jadwal_list = parse_jadwal_file()
    for jadwal in jadwal_list:
        if jadwal['header'] == 'Error':
            continue

        start_date, end_date = parse_date_from_header(jadwal['header'])

        if start_date and end_date and start_date <= target_date <= end_date:
            return jadwal

    return None


def get_jadwal_tomorrow() -> Optional[Dict]:
    """Get jadwal for tomorrow."""
    tomorrow = datetime.now(WIB).date() + timedelta(days=1)
    return get_jadwal_for_date(tomorrow)


def get_current_jadwal() -> Optional[Dict]:
    """Get jadwal for today."""
    today = datetime.now(WIB).date()
    return get_jadwal_for_date(today)


def get_jadwal_range(start_offset: int, end_offset: int) -> List[Dict]:
    """Get jadwal within a date range."""
    jadwal_list = parse_jadwal_file()
    result = []
    today = datetime.now(WIB).date()
    start = today + timedelta(days=start_offset)
    end = today + timedelta(days=end_offset)

    for jadwal in jadwal_list:
        if jadwal['header'] == 'Error':
            continue

        s_date, e_date = parse_date_from_header(jadwal['header'])
        if s_date and e_date and s_date <= end and e_date >= start:
            result.append(jadwal)

    return result


def get_jadwal_this_week() -> List[Dict]:
    """Get jadwal for this week."""
    today = datetime.now(WIB).date()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    jadwal_list = parse_jadwal_file()
    result = []
    for jadwal in jadwal_list:
        if jadwal['header'] == 'Error':
            continue
        s_date = jadwal.get('start_date')
        e_date = jadwal.get('end_date')
        if not s_date or not e_date:
            continue
        if s_date <= end and e_date >= start:
            result.append(jadwal)
    return result


def get_jadwal_next_week() -> List[Dict]:
    """Get jadwal for next week."""
    return get_jadwal_range(7, 13)


def find_jadwal_by_month(month: int, year: Optional[int] = None) -> List[Dict]:
    """Cari semua entry jadwal yang mencakup bulan (dan tahun) tertentu."""
    jadwal_list = parse_jadwal_file()
    result = []

    for jadwal in jadwal_list:
        if jadwal.get('header') == 'Error':
            continue
        s_date = jadwal.get('start_date')
        e_date = jadwal.get('end_date')
        if not s_date or not e_date:
            continue

        if year and s_date.year != year and e_date.year != year:
            continue

        d = s_date
        while d <= e_date:
            if d.month == month and (not year or d.year == year):
                result.append(jadwal)
                break
            d += timedelta(days=1)

    return result


def _is_uts_uas_entry(jadwal: Dict) -> tuple:
    """
    Cek apakah entry jadwal merupakan UTS atau UAS yang SEBENARNYA.
    Mengembalikan (True/False, tipe: 'UTS'|'UAS'|'').
    """
    header = jadwal.get('header', '').upper()

    if '=== UAS ===' in header or header.strip() == 'UAS':
        return True, 'UAS'
    if '=== UTS ===' in header or header.strip() == 'UTS':
        return True, 'UTS'

    return False, ''


def find_upcoming_uts_uas(exam_type: str) -> Optional[Dict]:
    """
    Cari entry UTS atau UAS yang SEBENARNYA (bukan persiapan).
    """
    exam_type = exam_type.upper()
    jadwal_list = parse_jadwal_file()
    today = datetime.now(WIB).date()

    upcoming = []
    past = []

    for jadwal in jadwal_list:
        if jadwal.get('header') == 'Error':
            continue

        is_exam, detected_type = _is_uts_uas_entry(jadwal)
        if not is_exam or detected_type != exam_type:
            continue

        s_date = jadwal.get('start_date')
        if not s_date:
            content_lines = jadwal.get('content', '').split('\n')
            for line in content_lines:
                start_date, end_date = parse_date_from_header(line.strip())
                if start_date:
                    s_date = start_date
                    e_date = end_date
                    jadwal['start_date'] = s_date
                    jadwal['end_date'] = e_date
                    break

        if not s_date:
            continue

        if s_date >= today:
            upcoming.append(jadwal)
        else:
            past.append(jadwal)

    if upcoming:
        return min(upcoming, key=lambda j: j['start_date'])

    if past:
        return max(past, key=lambda j: j['start_date'])

    return None


def get_jadwal_next_week_with_exam() -> List[Dict]:
    """
    Sama seperti get_jadwal_next_week() tetapi TIDAK membuang entry UTS/UAS.
    """
    return get_jadwal_range(7, 13)


def _format_exam_entry(jadwal: Dict, exam_type: str) -> str:
    """Format pesan khusus untuk entry UTS/UAS."""
    header = jadwal.get('header', '')
    content = jadwal.get('content', '')
    s_date = jadwal.get('start_date')
    e_date = jadwal.get('end_date')

    emoji = '📝' if exam_type == 'UTS' else '🎓'

    date_str = ''
    if s_date and e_date:
        date_str = f"{s_date.strftime('%d %B %Y')} – {e_date.strftime('%d %B %Y')}"
    elif s_date:
        date_str = s_date.strftime('%d %B %Y')

    msg = f"{emoji} **JADWAL {exam_type}**\n"
    if date_str:
        msg += f"📅 Tanggal: **{date_str}**\n"
    msg += f"\n{content}"

    return msg


# Background task helpers
def _get_general_channel(bot, GENERAL_CHANNEL_ID: int):
    """Ambil channel #general berdasarkan GENERAL_CHANNEL_ID, fallback ke system channel."""
    if GENERAL_CHANNEL_ID:
        channel = bot.get_channel(GENERAL_CHANNEL_ID)
        if channel:
            return channel
        logger.warning(f"⚠️ GENERAL_CHANNEL_ID={GENERAL_CHANNEL_ID} tidak ditemukan, fallback ke system channel")

    if not bot.guilds:
        return None

    guild = bot.guilds[0]
    return guild.system_channel or next(
        (ch for ch in guild.text_channels if ch.name == "general"),
        guild.text_channels[0] if guild.text_channels else None
    )


# Background tasks - need to be created with bot reference
daily_jadwal_reminder = None
uts_uas_reminder = None


def create_background_tasks(bot, GENERAL_CHANNEL_ID: int):
    """Create background tasks for jadwal reminders."""
    global daily_jadwal_reminder, uts_uas_reminder

    @tasks.loop(time=datetime.now(WIB).replace(hour=8, minute=0, second=0, microsecond=0).time())
    async def _daily_jadwal_reminder():
        logger.info("🔔 Daily jadwal reminder check")
        today = datetime.now(WIB).date()
        day_of_week = today.weekday()

        if day_of_week not in [0, 4]:
            logger.info(f"✅ Not reminder day ({today.strftime('%A')}), skip")
            return

        channel = _get_general_channel(bot, GENERAL_CHANNEL_ID)
        if not channel:
            logger.warning("❌ No channel available to send reminder")
            return

        jadwal_list = get_jadwal_this_week()

        if day_of_week == 0:
            if jadwal_list:
                await send_jadwal_list(
                    channel,
                    jadwal_list,
                    header="📅 **JADWAL KULIAH MINGGU INI**\nSelamat memulai pekan baru! Berikut jadwal kuliah minggu ini 👇\n\n"
                )
                logger.info("✅ Monday jadwal reminder sent")
            else:
                await channel.send("📅 Tidak ada jadwal kuliah untuk minggu ini.")
                logger.info("✅ Monday: no schedule this week")

        elif day_of_week == 4:
            if jadwal_list:
                await send_jadwal_list(
                    channel,
                    jadwal_list,
                    header="⏰ **REMINDER JADWAL KULIAH MINGGU INI**\nJangan lupa, masih ada kegiatan minggu ini 👇\n\n"
                )
                logger.info("✅ Friday reminder sent")
            else:
                await channel.send("⏰ Tidak ada jadwal kuliah tersisa untuk minggu ini.")

    @tasks.loop(time=datetime.now(WIB).replace(hour=8, minute=5, second=0, microsecond=0).time())
    async def _uts_uas_reminder():
        """
        Background task: kirim reminder 2 minggu sebelum UTS/UAS.
        Berjalan setiap hari Senin pukul 08:05 WIB.
        """
        today = datetime.now(WIB).date()
        if today.weekday() != 0:  # Hanya Senin
            return

        logger.info("🔔 UTS/UAS reminder check")

        channel = _get_general_channel(bot, GENERAL_CHANNEL_ID)
        if not channel:
            logger.warning("❌ No channel available for UTS/UAS reminder")
            return

        jadwal_list = parse_jadwal_file()
        reminder_window_start = today + timedelta(days=1)
        reminder_window_end = today + timedelta(days=14)

        for exam_label, emoji in [('UTS', '📝'), ('UAS', '🎓')]:
            for jadwal in jadwal_list:
                if jadwal.get('header') == 'Error':
                    continue

                is_exam, detected_type = _is_uts_uas_entry(jadwal)
                if not is_exam or detected_type != exam_label:
                    continue

                s_date = jadwal.get('start_date')
                if not s_date:
                    continue

                if reminder_window_start <= s_date <= reminder_window_end:
                    days_left = (s_date - today).days
                    header = jadwal.get('header', '')
                    content = jadwal.get('content', '')

                    msg = (
                        f"{emoji} **REMINDER {exam_label} — {days_left} HARI LAGI!**\n"
                        f"Halo semuanya! {exam_label} sudah semakin dekat. "
                        f"Yuk mulai persiapkan diri dari sekarang! 💪\n\n"
                        f"📅 **{s_date.strftime('%d %B %Y')}**\n```{content}```"
                    )
                    await channel.send(msg[:2000])
                    logger.info(f"✅ {exam_label} reminder sent ({days_left} days left)")

    daily_jadwal_reminder = _daily_jadwal_reminder
    uts_uas_reminder = _uts_uas_reminder

    return daily_jadwal_reminder, uts_uas_reminder


async def handle_jadwal_request(msg, user_prompt: str, bot_ref, GENERAL_CHANNEL_ID: int) -> bool:
    """Handle jadwal-related user requests."""
    from src.parser import parse_date_from_prompt, parse_month_year_from_prompt

    prompt_lower = user_prompt.lower()
    uts_keywords = ["uts", "ujian tengah semester", "mid exam", "mid-term"]
    uas_keywords = ["uas", "ujian akhir semester", "final exam"]

    if any(kw in prompt_lower for kw in uts_keywords) and \
       not any(kw in prompt_lower for kw in uas_keywords):
        # Request jadwal UTS
        jadwal = find_upcoming_uts_uas('UTS')
        if jadwal:
            await msg.channel.send(_format_exam_entry(jadwal, 'UTS')[:2000])
        else:
            await msg.channel.send("📝 Tidak ada data jadwal UTS ditemukan.")
        return True

    if any(kw in prompt_lower for kw in uas_keywords):
        # Request jadwal UAS
        jadwal = find_upcoming_uts_uas('UAS')
        if jadwal:
            await msg.channel.send(_format_exam_entry(jadwal, 'UAS')[:2000])
        else:
            await msg.channel.send("🎓 Tidak ada data jadwal UAS ditemukan.")
        return True

    # Detect General intent
    jadwal_intents = [
        "jadwal", "mata kuliah", "cek jadwal", "lihat jadwal", "info jadwal",
        "jadwal kuliah", "jadwal uas", "jadwal elearning",
        "jadwal minggu", "jadwal hari", "kapan kuliah", "uas kapan"
    ]

    if not any(intent in prompt_lower for intent in jadwal_intents):
        return False

    # Relative date handling
    now = datetime.now(WIB)
    if "bulan depan" in prompt_lower:
        next_month = (now.month % 12) + 1
        next_year = now.year + 1 if next_month == 1 else now.year
        jadwal_list = find_jadwal_by_month(next_month, next_year)
        month_name = datetime(next_year, next_month, 1).strftime('%B')
        header = f"📚 **JADWAL BULAN {month_name} {next_year}**\n\n"
        await send_jadwal_list(msg.channel, jadwal_list, header=header)
        return True

    if "minggu depan" in prompt_lower:
        jadwal_list = get_jadwal_next_week_with_exam()
        if not jadwal_list:
            await msg.channel.send("📚 Tidak ada jadwal untuk minggu depan.")
        else:
            exam_notes = []
            for j in jadwal_list:
                is_exam, etype = _is_uts_uas_entry(j)
                if is_exam:
                    exam_notes.append(etype)

            header = "📚 **JADWAL MINGGU DEPAN**\n\n"
            if exam_notes:
                unique_exams = list(dict.fromkeys(exam_notes))
                exams_str = " & ".join(unique_exams)
                header = (
                    f"📚 **JADWAL MINGGU DEPAN**\n"
                    f"⚠️ Minggu depan ada **{exams_str}** — siapkan dirimu! 💪\n\n"
                )
            await send_jadwal_list(msg.channel, jadwal_list, header=header)
        return True

    if "minggu ini" in prompt_lower:
        jadwal_list = get_jadwal_this_week()
        await send_jadwal_list(msg.channel, jadwal_list, header="📚 **JADWAL MINGGU INI**\n\n")
        return True

    if "besok" in prompt_lower:
        jadwal = get_jadwal_tomorrow()
        if jadwal:
            is_exam, etype = _is_uts_uas_entry(jadwal)
            if is_exam:
                await msg.channel.send(_format_exam_entry(jadwal, etype)[:2000])
            else:
                await msg.channel.send(
                    f"📚 **JADWAL UNTUK BESOK ({jadwal['header']})**\n\n```{jadwal['content']}```"
                )
        else:
            await msg.channel.send("📚 Tidak ada jadwal untuk besok.")
        return True

    if "hari ini" in prompt_lower or "sekarang" in prompt_lower:
        jadwal = get_current_jadwal()
        if jadwal:
            is_exam, etype = _is_uts_uas_entry(jadwal)
            if is_exam:
                await msg.channel.send(_format_exam_entry(jadwal, etype)[:2000])
            else:
                await msg.channel.send(
                    f"📚 **JADWAL UNTUK HARI INI ({jadwal['header']})**\n\n```{jadwal['content']}```"
                )
        else:
            await msg.channel.send("📚 Tidak ada jadwal untuk hari ini.")
        return True

    # Check (dd bulan [yyyy])
    specific_date = parse_date_from_prompt(user_prompt)
    if specific_date:
        jadwal = get_jadwal_for_date(specific_date)
        if jadwal:
            is_exam, etype = _is_uts_uas_entry(jadwal)
            if is_exam:
                resp = _format_exam_entry(jadwal, etype)
            else:
                resp = (
                    f"📚 **JADWAL UNTUK {specific_date.strftime('%d %B %Y')}**\n\n"
                    f"**{jadwal['header']}**\n```{jadwal['content']}```"
                )
        else:
            resp = f"📚 Tidak ada jadwal untuk tanggal {specific_date.strftime('%d %B %Y')}."
        await msg.channel.send(resp[:2000])
        return True

    # Check month
    month_info = parse_month_year_from_prompt(user_prompt)
    if month_info:
        month_num, year = month_info
        if year is None:
            year = now.year
        jadwal_list = find_jadwal_by_month(month_num, year)
        month_name = datetime(year, month_num, 1).strftime('%B')
        header = f"📚 **JADWAL BULAN {month_name} {year}**\n\n"
        await send_jadwal_list(msg.channel, jadwal_list, header=header)
        return True

    # Fallback
    jadwal = get_jadwal_this_week()
    if not jadwal:
        await msg.channel.send("📚 Tidak ada jadwal.")
        return True

    await send_jadwal_list(msg.channel, jadwal, header="📚 **JADWAL KULIAH**\n\n")
    return True