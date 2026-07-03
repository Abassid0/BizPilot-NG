"""
scripts/run_dev.py
-------------------
Local development runner.

In production (Railway/Render), the bot runs via webhook inside
FastAPI. Locally, we don't have a public HTTPS URL for Telegram
to push updates to, so we use long-polling instead.

This script:
  1. Starts FastAPI on localhost:8000 (for dashboard + API testing)
  2. Starts the Telegram bot in polling mode in a separate thread

Usage:
    python scripts/run_dev.py

Requirements:
    - .env file present and filled in
    - Dependencies installed: pip install -r requirements.txt
"""

import asyncio
import os
import sys
import threading
import uvicorn

# Make sure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# Force development mode
os.environ["APP_ENV"] = "development"


def run_fastapi():
    """Run FastAPI in a background thread."""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,   # reload=True conflicts with asyncio in threads
        log_level="warning",
    )


async def run_polling():
    """Run the Telegram bot in long-polling mode."""
    from app.bot.app import build_bot_app
    from app.core.config import settings

    logger.info("Starting Telegram bot in POLLING mode (development)")

    bot_app = build_bot_app()
    await bot_app.initialize()

    # Delete any existing webhook so polling works
    await bot_app.bot.delete_webhook(drop_pending_updates=True)
    logger.info(f"Bot username: @{(await bot_app.bot.get_me()).username}")

    await bot_app.start()
    await bot_app.updater.start_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )

    logger.info("Bot is running. Press Ctrl+C to stop.")

    try:
        # Keep running until interrupted
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping bot...")
    finally:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("  BizPilot NG — Development Mode")
    logger.info("  FastAPI:  http://localhost:8000")
    logger.info("  Docs:     http://localhost:8000/docs")
    logger.info("  Dashboard:http://localhost:8000/dashboard")
    logger.info("=" * 50)

    # Start FastAPI in a background thread
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()

    # Run the bot in the main asyncio event loop
    asyncio.run(run_polling())
