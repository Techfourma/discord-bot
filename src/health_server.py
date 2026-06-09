import logging
import threading
import time as py_time
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler for health checks."""

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
    """Run the health check server in a background thread."""
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"🌐 Health server running on port {port}")
    try:
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Health server error: {e}")


def start_health_server() -> threading.Thread:
    """Start the health server in a daemon thread."""
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    py_time.sleep(3)
    return health_thread