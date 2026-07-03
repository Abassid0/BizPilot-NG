"""
scripts/register_webhook.py
-----------------------------
One-time script to register the Telegram webhook after deploying.

Run this AFTER you have deployed to Railway/Render and your app
is live at a public HTTPS URL.

Usage:
    python scripts/register_webhook.py

It will:
  1. Delete any existing webhook
  2. Register the new webhook URL
  3. Print confirmation with webhook info
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from telegram import Bot
from app.core.config import settings


async def register():
    bot = Bot(token=settings.telegram_bot_token)

    print(f"\n{'='*55}")
    print(f"  BizPilot NG — Webhook Registration")
    print(f"{'='*55}")

    me = await bot.get_me()
    print(f"\n  Bot: @{me.username} (ID: {me.id})")
    print(f"  Webhook URL: {settings.webhook_url}")

    # Step 1: Delete existing webhook
    await bot.delete_webhook(drop_pending_updates=True)
    print("\n  ✓ Existing webhook deleted")

    # Step 2: Register new webhook
    success = await bot.set_webhook(
        url=settings.webhook_url,
        secret_token=settings.telegram_webhook_secret,
        allowed_updates=["message", "callback_query"],
        max_connections=40,
    )

    if success:
        print("  ✓ Webhook registered successfully")
    else:
        print("  ✗ Webhook registration failed")
        return

    # Step 3: Verify
    info = await bot.get_webhook_info()
    print(f"\n  Webhook Info:")
    print(f"    URL:               {info.url}")
    print(f"    Pending updates:   {info.pending_update_count}")
    print(f"    Last error:        {info.last_error_message or 'None'}")
    print(f"\n  ✅ Done. Your bot is live!\n")

    await bot.close()


if __name__ == "__main__":
    asyncio.run(register())
