try:
    import discord
    from discord.ext import commands, tasks
except ImportError:
    # allow the module to be imported in environments without discord
    class _Dummy:
        pass
    discord = _Dummy()
    commands = _Dummy()
    tasks = _Dummy()
import logging
import os
import time as py_time
import asyncio
from datetime import datetime, timedelta, time as dt_time, timezone 
from dotenv import load_dotenv
import aiohttp
from typing import Dict, Optional
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    from ai_bot_service import ai_bot_service
except ImportError:
    class MockAIBotService:
        async def get_response(self, prompt, user_id, image_bytes=None):
            return f"AI Response untuk: {prompt}"
    ai_bot_service = MockAIBotService()

print("🚀 Starting Techfour Bot")

# HEALTH SERVER
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/', '/health', '/kaithhealthcheck', '/healthcheck']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def run_health_server():
    port = 8080
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"🌐 Health server running on port {port}")
    try:
        server.serve_forever()
    except Exception as e:
        print(f"❌ Health server error: {e}")

health_thread = threading.Thread(target=run_health_server, daemon=True)
health_thread.start()
py_time.sleep(3)

# LOGGING
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ENVIRONMENT
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Webhook Logger
class WebhookLogger:
    def __init__(self, webhook_url: Optional[str]):
        self.webhook_url = webhook_url
        self.session = None

    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def send_log(self, content: str):
        if not self.webhook_url:
            return
        try:
            session = await self.get_session()
            payload = {"content": content[:2000]}
            async with session.post(self.webhook_url, json=payload) as resp:
                if resp.status not in (200, 204):
                    logger.error(f"❌ Webhook failed: {resp.status}")
        except Exception as e:
            logger.error(f"💥 Failed to send webhook: {e}")

webhook_logger = WebhookLogger(WEBHOOK_URL)

# TOKEN VALIDATION
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

# BOT Hanling error
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.presences = True

class TechfourBot(commands.Bot):
    async def on_ready(self):
        print(f'🎉 {self.user} is now ONLINE!')
        print(f'📊 Connected to {len(self.guilds)} guilds')

        # Set status bot
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="!help | Mentions"
            )
        )

        # Start background tasks
        try:
            daily_jadwal_reminder.start()
            print("✅ Background tasks started")
        except Exception as e:
            print(f"⚠️ Error starting tasks: {e}")

        logger.info(f"Bot {self.user} fully operational")

    async def on_connect(self):
        print("🔗 Connected to Discord gateway")

    async def on_disconnect(self):
        print("🔌 Disconnected from Discord gateway")

    async def on_error(self, event, *args, **kwargs):
        logger.error(f"Error in event {event}: {args}")

bot = TechfourBot(command_prefix="!", intents=intents)

# RATE LIMITER
class RateLimiter:
    def __init__(self):
        self.user_cooldowns: Dict[int, float] = {}
        self.user_daily_usage: Dict[int, int] = {}
        self.last_reset_time: float = py_time.time()
        self.DAILY_RESET_INTERVAL = 24 * 60 * 60

    def check_reset(self):
        now = py_time.time()
        if now - self.last_reset_time >= self.DAILY_RESET_INTERVAL:
            self.user_daily_usage.clear()
            self.last_reset_time = now
            logger.info("🔄 Daily usage reset")

    def get_daily_limit(self, is_admin: bool) -> int:
        return 20 if is_admin else 10

    async def can_use_ai(self, user_id: int, is_admin: bool):
        self.check_reset()
        now = py_time.time()

        # Cooldown check
        if user_id in self.user_cooldowns:
            diff = now - self.user_cooldowns[user_id]
            if diff < 10:
                return False, f"⏳ Tunggu {int(10-diff)} detik sebelum menggunakan AI lagi."

        # Daily limit check
        used = self.user_daily_usage.get(user_id, 0)
        limit = self.get_daily_limit(is_admin)
        if used >= limit:
            return False, f"🚫 Limit harian {used}/{limit} tercapai. Reset dalam 24 jam."

        return True, None

    async def record(self, user_id: int):
        self.user_cooldowns[user_id] = py_time.time()
        self.user_daily_usage[user_id] = self.user_daily_usage.get(user_id, 0) + 1

rate_limiter = RateLimiter()

# ACTIVITY TRACKER
class ActivityTracker:
    def __init__(self):
        self.last_activity = {}

    def update_activity(self, uid: int):
        self.last_activity[uid] = datetime.now()

activity_tracker = ActivityTracker()

def is_admin(member: discord.Member) -> bool:
    if member.guild.owner_id == member.id:
        return True
    admin_roles = ["admin", "administrator", "owner", "moderator"]
    return any(role.name.lower() in admin_roles for role in member.roles)

# JADWAL KULIAH
WIB = timezone(timedelta(hours=7))

# helper untuk mengirimkan daftar jadwal dalam beberapa pesan jika melebihi batas
async def send_jadwal_list(channel, jadwal_list, header: str = ""):
    """Kirimkan isi jadwal_list ke channel dengan header opsional.
    Membagi pesan menjadi beberapa kiriman agar tidak melampaui batas 2000 karakter.
    """
    if not jadwal_list:
        await channel.send("📚 Tidak ada jadwal.")
        return

    msg = header
    for j in jadwal_list:
        entry = f"**{j['header']}**\n```{j['content']}```\n\n"
        # jika menambahkan entry akan melebihi batas, kirim dulu apa yang ada
        if len(msg) + len(entry) > 1900:
            await channel.send(msg)
            msg = ""
        msg += entry
    if msg:
        await channel.send(msg)


def parse_jadwal_file():
    """Membaca dan memecah file jadwal, lalu mengeluarkan daftar entry.

    Setiap entry sekarang juga menyimpan tanggal awal/akhir yang diparsing
    sehingga pencarian berdasarkan bulan atau tanggal menjadi mudah.
    """
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

def parse_date_from_header(header: str):
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

def get_jadwal_for_date(target_date):
    jadwal_list = parse_jadwal_file()
    
    for jadwal in jadwal_list:
        if jadwal['header'] == 'Error':
            continue
            
        start_date, end_date = parse_date_from_header(jadwal['header'])
        
        if start_date and end_date and start_date <= target_date <= end_date:
            return jadwal
    
    return None

def get_jadwal_tomorrow():
    tomorrow = datetime.now(WIB).date() + timedelta(days=1)
    return get_jadwal_for_date(tomorrow)

def get_current_jadwal():
    today = datetime.now(WIB).date()
    return get_jadwal_for_date(today)

def get_jadwal_range(start_offset: int, end_offset: int):
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

def get_jadwal_this_week():
    return get_jadwal_range(0, 6)

def get_jadwal_next_week():
    return get_jadwal_range(7, 13)


def find_jadwal_by_month(month: int, year: Optional[int] = None):
    """Cari semua entry jadwal yang mencakup bulan (dan tahun) tertentu.

    Ditujukan untuk mendukung kueri "jadwal bulan maret" bahkan jika sudah
    lampau. Fungsi akan mengembalikan daftar entry yang mempunyai rentang
    tanggal di bulan tersebut. (Iterasi harian sederhana untuk menangani
    rentang yang melintasi akhir bulan/tahun.)
    """
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


def parse_date_from_prompt(prompt: str) -> Optional[datetime.date]:
    """Deteksi tanggal spesifik (DD Month [YYYY]) dari string.

    Contoh teks yang didukung:
      - "5 maret"
      - "tanggal 12 april 2025"
      - "20 December"
    Jika ditemukan, kembalikan objek date. Tahun default 2025 jika tidak
    disebutkan (sama seperti parser header jadwal sebelumnya).
    """
    month_map = {
        'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6,
        'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }

    # cari pola angka + nama bulan
    match = re.search(r"(\d{1,2})\s+([A-Za-z]+)(?:\s+(\d{4}))?", prompt)
    if not match:
        return None

    day = int(match.group(1))
    month_str = match.group(2).lower()
    month = month_map.get(month_str)
    year = int(match.group(3)) if match.group(3) else datetime.now(WIB).year

    if not month:
        return None

    try:
        return datetime(year, month, day).date()
    except ValueError:
        return None


def parse_month_year_from_prompt(prompt: str) -> Optional[tuple[int, Optional[int]]]:
    """Ekstrak nama bulan (dan opsional tahun) dari teks.

    Mengembalikan pasangan (bulan, tahun) atau None jika tidak ada bulan.
    """
    month_map = {
        'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6,
        'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }

    # cari nama bulan dalam teks
    for name, num in month_map.items():
        if re.search(r"\b" + re.escape(name) + r"\b", prompt.lower()):
            year_match = re.search(r"(\d{4})", prompt)
            year = int(year_match.group(1)) if year_match else datetime.now(WIB).year
            return num, year
    return None


# BACKGROUND TASKS
@tasks.loop(time=dt_time(hour=8, minute=0, tzinfo=WIB))
async def daily_jadwal_reminder():
    logger.info("🔔 Daily jadwal reminder check")
    
    if not bot.guilds:
        logger.warning("❌ No guilds available")
        return

    guild = bot.guilds[0]
    channel = guild.system_channel or guild.text_channels[0]

    today = datetime.now(WIB).date()
    day_of_week = today.weekday()

    # Reminder pada Jumat (4) dan Minggu (6)
    if day_of_week not in [4, 6]:
        logger.info(f"✅ Not reminder day ({today.strftime('%A')})")
        return
    
    jadwal = get_jadwal_tomorrow()

    if jadwal:
        response = f"⏰ **Pengingat Jadwal Kuliah Besok ({jadwal['header']}):**\n\n```{jadwal['content']}```"
        try:
            await channel.send(response)
            logger.info("✅ Reminder sent")
        except Exception as e:
            logger.error(f"❌ Failed to send reminder: {e}")
    else:
        logger.info("✅ No schedule for tomorrow")

# OCR HANDLER
async def handle_ocr_attachment(attachment, user_id: int, channel):
    try:
        if attachment.size > 5_000_000:
            await channel.send("❌ File terlalu besar (max 5MB).")
            return

        headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url, headers=headers, timeout=15) as resp:
                if resp.status != 200:
                    await channel.send(f"❌ Gagal download gambar. Status: {resp.status}")
                    return
                image_bytes = await resp.read()

        await channel.typing()
        ocr_result = await ai_bot_service.get_response(
            "Tolong ekstrak semua teks yang terlihat di gambar ini.",
            user_id,
            image_bytes=image_bytes
        )
        await channel.send(f"📄 **Hasil OCR:**\n{ocr_result[:1900]}")
        logger.info("✅ OCR completed")

    except Exception as e:
        logger.error(f"❌ OCR error: {e}")
        await channel.send("❌ Gagal memproses gambar.")

# JADWAL COMMAND HANDLER
async def handle_jadwal_request(msg, user_prompt: str) -> bool:
    prompt_lower = user_prompt.lower()

    # deteksi intent umum
    jadwal_intents = [
        "jadwal", "cek jadwal", "lihat jadwal", "info jadwal",
        "jadwal kuliah", "jadwal uas", "jadwal elearning",
        "jadwal minggu", "jadwal hari", "kapan kuliah", "uas kapan"
    ]

    if not any(intent in prompt_lower for intent in jadwal_intents):
        return False

    # waktu relatif (besok, hari ini, minggu ini, minggu depan)
    if "minggu depan" in prompt_lower:
        jadwal_list = get_jadwal_next_week()
        await send_jadwal_list(msg.channel, jadwal_list, header="📚 **JADWAL MINGGU DEPAN**\n\n")
        return True
    if "minggu ini" in prompt_lower:
        jadwal_list = get_jadwal_this_week()
        await send_jadwal_list(msg.channel, jadwal_list, header="📚 **JADWAL MINGGU INI**\n\n")
        return True
    if "besok" in prompt_lower:
        jadwal = get_jadwal_tomorrow()
        if jadwal:
            await msg.channel.send(
                f"📚 **JADWAL UNTUK BESOK ({jadwal['header']})**\n\n```{jadwal['content']}```"
            )
        else:
            await msg.channel.send("📚 Tidak ada jadwal untuk besok.")
        return True
    if "hari ini" in prompt_lower or "sekarang" in prompt_lower:
        jadwal = get_current_jadwal()
        if jadwal:
            await msg.channel.send(
                f"📚 **JADWAL UNTUK HARI INI ({jadwal['header']})**\n\n```{jadwal['content']}```"
            )
        else:
            await msg.channel.send("📚 Tidak ada jadwal untuk hari ini.")
        return True

    # 1. coba cek tanggal spesifik (dd bulan [yyyy])
    specific_date = parse_date_from_prompt(user_prompt)
    if specific_date:
        jadwal = get_jadwal_for_date(specific_date)
        if jadwal:
            resp = (
                f"📚 **JADWAL UNTUK {specific_date.strftime('%d %B %Y')}**\n\n"
                f"**{jadwal['header']}**\n```{jadwal['content']}```"
            )
        else:
            resp = (
                f"📚 Tidak ada jadwal untuk tanggal {specific_date.strftime('%d %B %Y')}.")
        await msg.channel.send(resp[:2000])
        return True

    # 2. cek bulan yang disebutkan
    month_info = parse_month_year_from_prompt(user_prompt)
    if month_info:
        month_num, year = month_info
        # default ke tahun sekarang jika tidak disebutkan
        if year is None:
            year = datetime.now(WIB).year
        jadwal_list = find_jadwal_by_month(month_num, year)
        month_name = datetime(year, month_num, 1).strftime('%B')
        header_prefix = f"📚 **JADWAL BULAN {month_name} {year}**\n\n"

        if jadwal_list:
            await send_jadwal_list(msg.channel, jadwal_list, header=header_prefix)
        else:
            await msg.channel.send(f"📚 Tidak ada jadwal untuk bulan {month_name} {year}.")
        return True

    # 3. fallback ke pencarian mingguan default
    jadwal = get_jadwal_this_week()
    if not jadwal:
        await msg.channel.send("📚 Tidak ada jadwal.")
        return True

    await send_jadwal_list(msg.channel, jadwal, header="📚 **JADWAL KULIAH**\n\n")
    return True

# MESSAGE HANDLER
@bot.event
async def on_message(msg):
    if msg.author == bot.user:
        return

    activity_tracker.update_activity(msg.author.id)

    # Toxic word filter
    toxic_words = ["kontol", "memek", "bangsat", "ngentod", "jembut", "anjing",
                   "brengsek", "tai", "tolol", "babi", "goblok", "ngewe"]
    if any(word in msg.content.lower() for word in toxic_words):
        try:
            await msg.delete()
            await msg.channel.send(f"{msg.author.mention} jaga bahasanya ya 🙏")
        except Exception as e:
            logger.error(f"❌ Delete message error: {e}")
        return

    # Handler untuk mention bot
    if bot.user.mentioned_in(msg) and not msg.mention_everyone:
        user_prompt = msg.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()

        # Handler OCR - priority
        if msg.attachments:
            for attachment in msg.attachments:
                if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".pdf")):
                    await handle_ocr_attachment(attachment, msg.author.id, msg.channel)
                    return

        # Priority 2: Jadwal
        if await handle_jadwal_request(msg, user_prompt):
            return
        
        # Priority 3: AI
        if not user_prompt:
            await msg.channel.send("Halo! Ada yang bisa kubantu?")
            return

        admin = is_admin(msg.author)
        can_use, error_msg = await rate_limiter.can_use_ai(msg.author.id, admin)
        
        if not can_use:
            await msg.channel.send(error_msg)
            return

        await msg.channel.typing()
        await rate_limiter.record(msg.author.id)
        
        reply = await ai_bot_service.get_response(user_prompt, msg.author.id, image_bytes=None)
        await msg.channel.send(reply[:2000])
        return

    await bot.process_commands(msg)

#Run bot error handling
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