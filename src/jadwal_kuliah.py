import logging
import re
import os
from datetime import datetime, timedelta, timezone as dt_timezone, time as dt_time, date
from typing import Dict, List, Optional, Tuple
from discord.ext import tasks

logger = logging.getLogger(__name__)
WIB = dt_timezone(timedelta(hours=7))

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__)) 
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)                   

def _find_collection_file() -> str:
    candidates = [
        os.path.join(SCRIPT_DIR, 'collection_data.txt'),  
        '/app/src/collection_data.txt',                   
        os.path.join(PROJECT_ROOT, 'collection_data.txt'),
        '/workspace/collection_data.txt',                 
        '/app/collection_data.txt',                       
        './collection_data.txt',                          
        os.path.join(os.getcwd(), 'collection_data.txt'), 
    ]

    for path in candidates:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            logger.info(f"✅ Found collection file at: {abs_path}")
            return abs_path

    fallback_paths = [
        '/app/src/collection_data.txt',
        '/workspace/src/collection_data.txt',
        '/workspace/collection_data.txt',
        '/app/collection_data.txt',
    ]
    for fb in fallback_paths:
        if os.path.exists(fb):
            fallback = fb
            break
    else:
        fallback = os.path.join(SCRIPT_DIR, 'collection_data.txt')

    logger.warning(f"⚠️ collection_data.txt not found. Tried: {candidates}. Using fallback: {fallback}")
    return fallback

# Constants
MONTH_MAP: Dict[str, int] = {
    'januari': 1,  'februari': 2,  'maret': 3,    'april': 4,
    'mei': 5,      'juni': 6,      'juli': 7,      'agustus': 8,
    'september': 9,'oktober': 10,  'november': 11, 'desember': 12,
    'january': 1,  'february': 2,  'march': 3,     'may': 5,
    'june': 6,     'july': 7,      'august': 8,    'october': 10,
    'december': 12,
}

_SKIP_HEADERS = {
    'jadwal kuliah kelas tple04',
    'semester 2 - ganjil',
    'semester genap 2025/2026',
    '=== description ===',
}

# Date parsing
def parse_date_from_header(header: str) -> Tuple[Optional[date], Optional[date]]:
    try:
        # ── Pattern 1: "DD Month - DD Month [YYYY]" ──────────────────────────
        m = re.search(
            r'(\d{1,2})\s+([A-Za-z]+)\s*-\s*(\d{1,2})\s+([A-Za-z]+)(?:\s+(\d{4}))?',
            header
        )
        if m:
            sm = MONTH_MAP.get(m.group(2).lower())
            em = MONTH_MAP.get(m.group(4).lower())
            if sm and em:
                yr_m = re.search(r'(\d{4})', header)
                y = int(yr_m.group(1)) if yr_m else datetime.now(WIB).year
                # Jika bulan akhir < bulan awal → melewati tahun baru
                ey = y + 1 if em < sm else y
                return date(y, sm, int(m.group(1))), date(ey, em, int(m.group(3)))

        # ── Pattern 2: "DayName, DD Month YYYY" ─────────────────────────────
        m2 = re.search(r'[A-Za-z]+,\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', header)
        if m2:
            mn = MONTH_MAP.get(m2.group(2).lower())
            if mn:
                d = date(int(m2.group(3)), mn, int(m2.group(1)))
                return d, d

        # ── Pattern 3: "DD Month YYYY" (single date) ────────────────────────
        m3 = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', header)
        if m3:
            mn = MONTH_MAP.get(m3.group(2).lower())
            if mn:
                d = date(int(m3.group(3)), mn, int(m3.group(1)))
                return d, d

        return None, None

    except Exception as e:
        logger.debug(f"parse_date_from_header error for {header!r}: {e}")
        return None, None


def _parse_dates_from_content(content: str) -> Tuple[Optional[date], Optional[date]]:
    """Scan baris-baris content untuk menemukan tanggal (dipakai untuk === UTS ===, UAS, dll)."""
    for line in content.split('\n'):
        s, e = parse_date_from_header(line.strip())
        if s:
            return s, e
    return None, None

# File parsing
def parse_collection_file() -> List[Dict]:
    collection_path = _find_collection_file()
    try:
        with open(collection_path, 'r', encoding='utf-8') as f:
            raw = f.read()
    except FileNotFoundError:
        logger.error(f"❌ File tidak ditemukan: {collection_path}")
        return []
    except Exception as e:
        logger.error(f"❌ Gagal membaca file: {e}")
        return []

    sections = re.split(r'-{3,}\s*\n', raw)
    jadwal_list: List[Dict] = []

    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue

        parts = sec.split('\n', 1)
        header  = parts[0].strip()
        content = parts[1].strip() if len(parts) > 1 else ''

        if header.lower() in _SKIP_HEADERS:
            continue

        s_date, e_date = parse_date_from_header(header)

        if not s_date:
            s_date, e_date = _parse_dates_from_content(content)

        jadwal_list.append({
            'header':     header,
            'content':    content,
            'start_date': s_date,
            'end_date':   e_date,
        })

    logger.info(f"✅ Parsed {len(jadwal_list)} jadwal entries dari {collection_path}")
    return jadwal_list

# UTS / UAS detection
def _is_uts_uas_entry(jadwal: Dict) -> Tuple[bool, str]:
    """
    Deteksi apakah entry adalah UTS atau UAS.
    Mendukung header: "=== UAS ===", "UAS", "=== UTS ===", "UTS"
    dan keyword di content sebagai fallback.
    """
    header  = jadwal.get('header', '').strip().upper()
    content = jadwal.get('content', '').upper()

    # Exact / contained match di header
    if header in ('=== UAS ===', 'UAS') or 'UJIAN AKHIR SEMESTER' in header:
        return True, 'UAS'
    if header in ('=== UTS ===', 'UTS') or 'UJIAN TENGAH SEMESTER' in header:
        return True, 'UTS'

    if 'UJIAN AKHIR SEMESTER' in content or '(UAS)' in content:
        return True, 'UAS'
    if 'UJIAN TENGAH SEMESTER' in content or '(UTS)' in content:
        return True, 'UTS'

    return False, ''

# Query functions
def get_jadwal_for_date(target_date: date) -> Optional[Dict]:
    """Jadwal yang mencakup tanggal tertentu."""
    for j in parse_collection_file():
        s, e = j['start_date'], j['end_date']
        if s and e and s <= target_date <= e:
            return j
    return None


def get_current_jadwal() -> Optional[Dict]:
    return get_jadwal_for_date(datetime.now(WIB).date())


def get_jadwal_tomorrow() -> Optional[Dict]:
    return get_jadwal_for_date(datetime.now(WIB).date() + timedelta(days=1))


def get_jadwal_this_week() -> List[Dict]:
    today = datetime.now(WIB).date()
    week_start = today - timedelta(days=today.weekday())   # Senin
    week_end   = week_start + timedelta(days=6)             # Minggu
    result = []
    for j in parse_collection_file():
        s, e = j['start_date'], j['end_date']
        if s and e and s <= week_end and e >= week_start:
            result.append(j)
    return result


def get_jadwal_remaining_this_week() -> List[Dict]:
    today = datetime.now(WIB).date()
    week_end = today - timedelta(days=today.weekday()) + timedelta(days=6)
    result = []
    for j in parse_collection_file():
        s, e = j['start_date'], j['end_date']
        if s and e and e >= today and s <= week_end:
            result.append(j)
    return result


def get_jadwal_next_week() -> List[Dict]:
    today = datetime.now(WIB).date()
    days_to_monday = (7 - today.weekday()) % 7 or 7
    next_monday = today + timedelta(days=days_to_monday)
    next_sunday = next_monday + timedelta(days=6)
    result = []
    for j in parse_collection_file():
        s, e = j['start_date'], j['end_date']
        if s and e and s <= next_sunday and e >= next_monday:
            result.append(j)
    return result


def get_jadwal_next_week_with_exam() -> List[Dict]:
    return get_jadwal_next_week()


def find_jadwal_by_month(month: int, year: int) -> List[Dict]:
    from calendar import monthrange as _monthrange
    _, last_day = _monthrange(year, month)
    month_start = date(year, month, 1)
    month_end   = date(year, month, last_day)

    result = []
    for j in parse_collection_file():
        s, e = j['start_date'], j['end_date']
        if s and e and s <= month_end and e >= month_start:
            result.append(j)
    return result


def find_upcoming_uts_uas(exam_type: str) -> Optional[Dict]:
    exam_type = exam_type.upper()
    today     = datetime.now(WIB).date()
    upcoming, past, no_date = [], [], []

    for j in parse_collection_file():
        is_exam, detected = _is_uts_uas_entry(j)
        if not is_exam or detected != exam_type:
            continue

        s = j.get('start_date')
        if not s:
            no_date.append(j)
            continue

        if s >= today:
            upcoming.append(j)
        else:
            past.append(j)

    if upcoming:
        return min(upcoming, key=lambda j: j['start_date'])
    if past:
        return max(past, key=lambda j: j['start_date'])
    if no_date:
        return no_date[0]
    return None

# Formatting
def _format_exam_entry(jadwal: Dict, exam_type: str) -> str:
    content = jadwal.get('content', '')
    s = jadwal.get('start_date')
    e = jadwal.get('end_date')
    emoji = '📝' if exam_type == 'UTS' else '🎓'

    if s and e and s != e:
        date_str = f"{s.strftime('%d %B %Y')} – {e.strftime('%d %B %Y')}"
    elif s:
        date_str = s.strftime('%d %B %Y')
    else:
        date_str = ''

    msg = f"{emoji} **JADWAL {exam_type}**\n"
    if date_str:
        msg += f"📅 Tanggal: **{date_str}**\n"
    msg += f"\n{content}"
    return msg


def format_jadwal_entry(jadwal: Dict) -> str:
    """Format satu entry jadwal untuk dikirim ke Discord."""
    header  = jadwal['header']
    content = jadwal['content']

    h_lower = header.lower()
    if h_lower.startswith('e-learning '):
        lines = content.split('\n')
        tatap_idx = next(
            (i for i, l in enumerate(lines) if l.lower().startswith('tatap muka')),
            None
        )
        if tatap_idx is not None:
            elearn_part  = '\n'.join(lines[:tatap_idx]).strip()
            tatap_header = lines[tatap_idx].strip()
            tatap_body   = '\n'.join(lines[tatap_idx+1:]).strip()
            result = f"__**{header}**__\n"
            if elearn_part:
                result += f"`{elearn_part}`\n"
            result += f"\n__**{tatap_header}**__\n"
            if tatap_body:
                result += f"`{tatap_body}`\n"
            return result

    return f"__**{header}**__\n`{content}`\n"


async def send_jadwal_list(channel, jadwal_list: List[Dict], header: str = '') -> None:
    if not jadwal_list:
        await channel.send("📚 Tidak ada jadwal.")
        return

    msg = header
    for j in jadwal_list:
        entry = format_jadwal_entry(j)
        if len(msg) + len(entry) > 1900:
            await channel.send(msg)
            msg = ''
        msg += entry

    if msg:
        await channel.send(msg)

# Background tasks
def _get_general_channel(bot, channel_id: int):
    if channel_id:
        ch = bot.get_channel(channel_id)
        if ch:
            return ch
        logger.warning(f"⚠️ Channel ID {channel_id} tidak ditemukan, fallback ke system channel")

    if not bot.guilds:
        return None
    guild = bot.guilds[0]
    return guild.system_channel or next(
        (c for c in guild.text_channels if c.name == 'general'),
        guild.text_channels[0] if guild.text_channels else None
    )


daily_jadwal_reminder = None
uts_uas_reminder      = None


def create_background_tasks(bot, GENERAL_CHANNEL_ID: int):
    global daily_jadwal_reminder, uts_uas_reminder

    REMINDER_TIME = dt_time(hour=8, minute=0, second=0, tzinfo=WIB)
    UTS_UAS_TIME  = dt_time(hour=8, minute=5, second=0, tzinfo=WIB)

    @tasks.loop(time=REMINDER_TIME)
    async def _daily_jadwal_reminder():
        today      = datetime.now(WIB).date()
        day_of_week = today.weekday()   # 0=Senin … 4=Jumat

        if day_of_week not in (0, 4):
            logger.info(f"ℹ️ Skip reminder — hari ini {today.strftime('%A')}")
            return

        logger.info(f"🔔 Daily reminder check — {today.strftime('%A %d %B %Y')}")
        channel = _get_general_channel(bot, GENERAL_CHANNEL_ID)
        if not channel:
            logger.warning("❌ Channel tidak ditemukan untuk reminder")
            return

        if day_of_week == 0:           
            jadwal_list = get_jadwal_this_week()
            if jadwal_list:
                await send_jadwal_list(
                    channel, jadwal_list,
                    header="📅 **JADWAL KULIAH MINGGU INI**\n"
                           "Selamat memulai pekan baru! Berikut jadwal kuliah minggu ini 👇\n\n"
                )
                logger.info("✅ Senin: reminder minggu ini terkirim")
            else:
                await channel.send("📅 Tidak ada jadwal kuliah untuk minggu ini.")
                logger.info("✅ Senin: tidak ada jadwal minggu ini")

        elif day_of_week == 4:          # ── Jumat ──
            jadwal_list = get_jadwal_remaining_this_week()
            if jadwal_list:
                await send_jadwal_list(
                    channel, jadwal_list,
                    header="⏰ **REMINDER JADWAL KULIAH MINGGU INI**\n"
                           "Jangan lupa, masih ada kegiatan minggu ini 👇\n\n"
                )
                logger.info("✅ Jumat: reminder sisa minggu terkirim")
            else:
                await channel.send("⏰ Tidak ada jadwal kuliah tersisa untuk minggu ini.")
                logger.info("✅ Jumat: tidak ada sisa jadwal")

    @tasks.loop(time=UTS_UAS_TIME)
    async def _uts_uas_reminder():
        today = datetime.now(WIB).date()
        if today.weekday() != 0:        # Hanya Senin
            return

        logger.info("🔔 UTS/UAS reminder check")
        channel = _get_general_channel(bot, GENERAL_CHANNEL_ID)
        if not channel:
            logger.warning("❌ Channel tidak ditemukan untuk UTS/UAS reminder")
            return

        window_start = today + timedelta(days=1)
        window_end   = today + timedelta(days=14)

        for exam_label, emoji in (('UTS', '📝'), ('UAS', '🎓')):
            for j in parse_jadwal_file():
                is_exam, detected = _is_uts_uas_entry(j)
                if not is_exam or detected != exam_label:
                    continue
                s = j.get('start_date')
                if not s:
                    continue
                if window_start <= s <= window_end:
                    days_left = (s - today).days
                    msg = (
                        f"{emoji} **REMINDER {exam_label} — {days_left} HARI LAGI!**\n"
                        f"Halo semuanya! {exam_label} sudah semakin dekat. "
                        f"Yuk mulai persiapkan diri dari sekarang! 💪\n\n"
                        f"📅 **{s.strftime('%d %B %Y')}**\n```{j.get('content', '')}```"
                    )
                    await channel.send(msg[:2000])
                    logger.info(f"✅ {exam_label} reminder terkirim ({days_left} hari lagi)")

    daily_jadwal_reminder = _daily_jadwal_reminder
    uts_uas_reminder      = _uts_uas_reminder

    return daily_jadwal_reminder, uts_uas_reminder

# User request handler
async def handle_jadwal_request(msg, user_prompt: str, bot_ref, GENERAL_CHANNEL_ID: int) -> bool:
    """
    Handle semua pesan user yang berkaitan dengan jadwal.
    Kembalikan True jika pesan ditangani, False jika bukan jadwal request.
    """
    from src.parser import parse_date_from_prompt, parse_month_year_from_prompt

    prompt_lower = user_prompt.lower()
    now          = datetime.now(WIB)

    uts_kw = ['uts', 'ujian tengah semester', 'mid exam', 'mid-term']
    uas_kw = ['uas', 'ujian akhir semester', 'final exam', 'uas kapan', 'kapan uas']

    is_uts = any(kw in prompt_lower for kw in uts_kw)
    is_uas = any(kw in prompt_lower for kw in uas_kw)

    if is_uts and not is_uas:
        jadwal = find_upcoming_uts_uas('UTS')
        if jadwal:
            await msg.channel.send(_format_exam_entry(jadwal, 'UTS')[:2000])
        else:
            await msg.channel.send("📝 Tidak ada data jadwal UTS ditemukan.")
        return True

    if is_uas:
        jadwal = find_upcoming_uts_uas('UAS')
        if jadwal:
            await msg.channel.send(_format_exam_entry(jadwal, 'UAS')[:2000])
        else:
            await msg.channel.send("🎓 Tidak ada data jadwal UAS ditemukan.")
        return True

    jadwal_intents = [
        'jadwal', 'mata kuliah', 'cek jadwal', 'lihat jadwal', 'info jadwal',
        'jadwal kuliah', 'jadwal elearning', 'jadwal minggu', 'jadwal hari',
        'kapan kuliah', 'minggu ini', 'minggu depan', 'bulan ini', 'bulan depan',
    ]
    if not any(intent in prompt_lower for intent in jadwal_intents):
        return False

    if 'bulan depan' in prompt_lower:
        next_month = (now.month % 12) + 1
        next_year  = now.year + 1 if next_month == 1 else now.year
        jadwal_list = find_jadwal_by_month(next_month, next_year)
        month_name  = datetime(next_year, next_month, 1).strftime('%B').upper()
        await send_jadwal_list(
            msg.channel, jadwal_list,
            header=f"📚 **JADWAL BULAN {month_name} {next_year}**\n\n"
        )
        return True

    if 'bulan ini' in prompt_lower:
        jadwal_list = find_jadwal_by_month(now.month, now.year)
        month_name  = now.strftime('%B').upper()
        await send_jadwal_list(
            msg.channel, jadwal_list,
            header=f"📚 **JADWAL BULAN {month_name} {now.year}**\n\n"
        )
        return True

    if 'minggu depan' in prompt_lower:
        jadwal_list = get_jadwal_next_week()
        if not jadwal_list:
            await msg.channel.send("📚 Tidak ada jadwal untuk minggu depan.")
            return True

        exam_types = []
        for j in jadwal_list:
            is_exam, etype = _is_uts_uas_entry(j)
            if is_exam:
                exam_types.append(etype)

        header = "📚 **JADWAL MINGGU DEPAN**\n\n"
        if exam_types:
            unique = list(dict.fromkeys(exam_types))
            header = (
                f"📚 **JADWAL MINGGU DEPAN**\n"
                f"⚠️ Minggu depan ada **{' & '.join(unique)}** — siapkan dirimu! 💪\n\n"
            )
        await send_jadwal_list(msg.channel, jadwal_list, header=header)
        return True

    if 'minggu ini' in prompt_lower:
        jadwal_list = get_jadwal_this_week()
        await send_jadwal_list(
            msg.channel, jadwal_list,
            header="📚 **JADWAL MINGGU INI**\n\n"
        )
        return True

    if 'besok' in prompt_lower:
        jadwal = get_jadwal_tomorrow()
        if jadwal:
            is_exam, etype = _is_uts_uas_entry(jadwal)
            if is_exam:
                await msg.channel.send(_format_exam_entry(jadwal, etype)[:2000])
            else:
                await msg.channel.send(
                    f"📚 **JADWAL BESOK ({jadwal['header']})**\n\n```{jadwal['content']}```"
                )
        else:
            await msg.channel.send("📚 Tidak ada jadwal untuk besok.")
        return True

    if 'hari ini' in prompt_lower or 'sekarang' in prompt_lower:
        jadwal = get_current_jadwal()
        if jadwal:
            is_exam, etype = _is_uts_uas_entry(jadwal)
            if is_exam:
                await msg.channel.send(_format_exam_entry(jadwal, etype)[:2000])
            else:
                await msg.channel.send(
                    f"📚 **JADWAL HARI INI ({jadwal['header']})**\n\n```{jadwal['content']}```"
                )
        else:
            await msg.channel.send("📚 Tidak ada jadwal untuk hari ini.")
        return True

    specific_date = parse_date_from_prompt(user_prompt)
    if specific_date:
        jadwal = get_jadwal_for_date(specific_date)
        if jadwal:
            is_exam, etype = _is_uts_uas_entry(jadwal)
            if is_exam:
                resp = _format_exam_entry(jadwal, etype)
            else:
                resp = (
                    f"📚 **JADWAL {specific_date.strftime('%d %B %Y')}**\n\n"
                    f"**{jadwal['header']}**\n```{jadwal['content']}```"
                )
        else:
            resp = f"📚 Tidak ada jadwal untuk tanggal {specific_date.strftime('%d %B %Y')}."
        await msg.channel.send(resp[:2000])
        return True

    month_info = parse_month_year_from_prompt(user_prompt)
    if month_info:
        month_num, year = month_info
        if not year:
            year = now.year
        jadwal_list = find_jadwal_by_month(month_num, year)
        month_name  = datetime(year, month_num, 1).strftime('%B').upper()
        await send_jadwal_list(
            msg.channel, jadwal_list,
            header=f"📚 **JADWAL BULAN {month_name} {year}**\n\n"
        )
        return True

    jadwal_list = get_jadwal_this_week()
    await send_jadwal_list(msg.channel, jadwal_list, header="📚 **JADWAL KULIAH**\n\n")
    return True