"""
app/main.py
------------
FastAPI application entry point.

On startup:
  1. Connects Supabase
  2. Builds the Telegram bot application
  3. Registers the webhook with Telegram

On shutdown:
  1. Cleanly stops the bot application
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger
import uvicorn

from app.core.config import settings
from app.api.routes.webhooks import router as webhook_router
from app.api.routes.dashboard import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle manager."""

    # ── Startup ──
    logger.info(f"Starting BizPilot NG in {settings.app_env} mode")

    # Build and initialise the Telegram bot application
    from app.bot.app import build_bot_app
    bot_app = build_bot_app()
    await bot_app.initialize()
    await bot_app.start()
    app.state.bot_app = bot_app

    # Register the webhook with Telegram
    if settings.is_production:
        await bot_app.bot.set_webhook(
            url=settings.webhook_url,
            secret_token=settings.telegram_webhook_secret,
            allowed_updates=["message", "callback_query", "inline_query"],
        )
        logger.info(f"Telegram webhook registered: {settings.webhook_url}")
    else:
        # In development, delete any existing webhook so polling works
        await bot_app.bot.delete_webhook()
        logger.info("Development mode — webhook deleted (use polling instead)")

    logger.info("BizPilot NG startup complete")
    yield  # ← Application runs here

    # ── Shutdown ──
    logger.info("Shutting down BizPilot NG...")
    await bot_app.stop()
    await bot_app.shutdown()
    logger.info("Shutdown complete")


# ── Create FastAPI App ────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="BizPilot NG",
        description="AI-powered business document assistant for Nigerian entrepreneurs",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # ── CORS (allows web dashboard to call the API) ───────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.webhook_base_url,
            "http://localhost:3000",   # Local dashboard dev
            "http://localhost:5173",   # Vite dev server
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Routes ────────────────────────────────────────────────
    app.include_router(webhook_router)
    app.include_router(dashboard_router)

    # ── Serve web dashboard static files ─────────────────────────
    # The built dashboard sits in /dashboard/dist
    import os
    dashboard_dist = os.path.join(os.path.dirname(__file__), "..", "dashboard", "dist")
    if os.path.exists(dashboard_dist):
        app.mount("/dashboard", StaticFiles(directory=dashboard_dist, html=True), name="dashboard")
        logger.info("Web dashboard static files mounted at /dashboard")

    # ── Payment success redirect page ────────────────────────────
    @app.get("/payment/success")
    async def payment_success():
        return {
            "message": "Payment successful! Return to Telegram and your plan will activate within 60 seconds.",
            "status": "success",
        }

    @app.get("/")
    async def root():
        return {
            "service": "BizPilot NG",
            "status":  "running",
            "version": "1.0.0",
            "docs":    "/docs" if settings.debug else "disabled",
        }

    return app


app = create_app()


# ── Development Entry Point ───────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level="info",
    )
