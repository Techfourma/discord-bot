import logging
import os
import aiohttp
from typing import Optional

logger = logging.getLogger(__name__)

class WebhookLogger:
    """Send logs to Discord webhook."""

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


# Initialize webhook logger
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
webhook_logger = WebhookLogger(WEBHOOK_URL)


def setup_logging():
    """Configure logging format and level."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )