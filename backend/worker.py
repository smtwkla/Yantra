"""Background worker — separate process from Gunicorn.

Placeholder until Yantra has scheduled tasks or a task_queue to drain: it idles
so the worker container stays up instead of exiting and being restarted in a
loop by Docker (restart: unless-stopped). Logs once at startup and then an
hourly heartbeat, to keep shipped logs quiet.

Run with:  python worker.py   (container: .venv/bin/python worker.py)
"""

import logging
import signal
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("worker")

HEARTBEAT_SECONDS = 3600

_running = True


def _stop(signum, _frame):
    """Exit the idle loop on SIGTERM/SIGINT so docker stop returns promptly."""
    global _running
    logger.info("Received signal %s, shutting down", signum)
    _running = False


def main():
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    logger.info("Worker started — idle (no tasks registered yet)")
    last_heartbeat = time.monotonic()
    while _running:
        time.sleep(1)
        if time.monotonic() - last_heartbeat >= HEARTBEAT_SECONDS:
            logger.info("idle")
            last_heartbeat = time.monotonic()
    logger.info("Worker stopped")


if __name__ == "__main__":
    main()
