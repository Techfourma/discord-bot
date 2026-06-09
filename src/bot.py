import logging
import time as py_time
from datetime import datetime, timezone, timedelta
from typing import Dict
import discord
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)

# Timezone
WIB = timezone(timedelta(hours=7))


class RateLimiter:
    """Rate limiter for AI usage."""

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


class ActivityTracker:
    """Track user activity."""

    def __init__(self):
        self.last_activity = {}

    def update_activity(self, uid: int):
        self.last_activity[uid] = datetime.now()


def is_admin(member: discord.Member) -> bool:
    """Check if member is an admin."""
    if member.guild.owner_id == member.id:
        return True
    admin_roles = ["admin", "administrator", "owner", "moderator"]
    return any(role.name.lower() in admin_roles for role in member.roles)


class TechfourBot(commands.Bot):
    """Main bot class with error handling and lifecycle events."""

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
            from src.jadwal_kuliah import daily_jadwal_reminder, uts_uas_reminder
            if daily_jadwal_reminder and not daily_jadwal_reminder.is_running():
                daily_jadwal_reminder.start()
            if uts_uas_reminder and not uts_uas_reminder.is_running():
                uts_uas_reminder.start()
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


# Initialize instances
rate_limiter = RateLimiter()
activity_tracker = ActivityTracker()

# Bot instance (will be configured later with intents)
bot = None


def create_bot(intents: discord.Intents) -> TechfourBot:
    """Create and configure the bot instance."""
    global bot
    bot = TechfourBot(command_prefix="!", intents=intents)
    return bot