"""
app/services/payments/email.py
--------------------------------
Transactional email via Resend.
Handles: welcome, payment confirmation, usage warnings, receipts.
"""

from __future__ import annotations

from typing import Optional
from loguru import logger

from app.core.config import settings


async def send_email(
    to: str,
    subject: str,
    html_body: str,
) -> bool:
    """
    Send a transactional email via Resend.
    Returns True on success.
    """
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set — email skipped")
        return False

    try:
        import resend
        resend.api_key = settings.resend_api_key

        resend.Emails.send({
            "from":    f"{settings.email_from_name} <{settings.email_from}>",
            "to":      [to],
            "subject": subject,
            "html":    html_body,
        })
        logger.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Resend email error: {e}")
        return False


async def send_welcome_email(to: str, name: str) -> bool:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#1B5E20;padding:30px;text-align:center;">
        <h1 style="color:white;margin:0;">Welcome to BizPilot NG 🚀</h1>
      </div>
      <div style="padding:30px;">
        <p>Hi <strong>{name}</strong>,</p>
        <p>Your BizPilot NG account is ready. You can now generate professional Nigerian business documents in seconds directly from Telegram.</p>
        <h3>What you can do right now:</h3>
        <ul>
          <li>📄 Generate invoices with automatic VAT & WHT</li>
          <li>📋 Write winning business proposals</li>
          <li>📝 Create contracts and NDAs</li>
          <li>📱 Generate social media content</li>
          <li>📊 Write business plan summaries for loan applications</li>
        </ul>
        <p>You start with <strong>5 free documents per month</strong>. Upgrade to Pro for unlimited access.</p>
        <p>Open Telegram and type <strong>/help</strong> to get started.</p>
      </div>
      <div style="background:#f5f5f5;padding:20px;text-align:center;font-size:12px;color:#888;">
        BizPilot NG — Powering Nigerian Entrepreneurs with AI
      </div>
    </div>
    """
    return await send_email(to, "Welcome to BizPilot NG 🚀", html)


async def send_payment_confirmation(
    to: str,
    name: str,
    plan_name: str,
    amount: str,
    reference: str,
) -> bool:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#1B5E20;padding:30px;text-align:center;">
        <h1 style="color:white;margin:0;">Payment Confirmed ✅</h1>
      </div>
      <div style="padding:30px;">
        <p>Hi <strong>{name}</strong>,</p>
        <p>Your payment has been received. Here are your receipt details:</p>
        <table style="width:100%;border-collapse:collapse;">
          <tr><td style="padding:8px;border-bottom:1px solid #eee;"><strong>Plan</strong></td><td style="padding:8px;border-bottom:1px solid #eee;">{plan_name}</td></tr>
          <tr><td style="padding:8px;border-bottom:1px solid #eee;"><strong>Amount</strong></td><td style="padding:8px;border-bottom:1px solid #eee;">{amount}</td></tr>
          <tr><td style="padding:8px;"><strong>Reference</strong></td><td style="padding:8px;">{reference}</td></tr>
        </table>
        <p>Your subscription is now active. Return to Telegram and start generating unlimited documents!</p>
      </div>
      <div style="background:#f5f5f5;padding:20px;text-align:center;font-size:12px;color:#888;">
        BizPilot NG | support@bizpilot.ng
      </div>
    </div>
    """
    return await send_email(to, f"BizPilot NG — Payment Receipt ({reference})", html)


async def send_usage_warning(to: str, name: str, used: int, limit: int) -> bool:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#E65100;padding:30px;text-align:center;">
        <h1 style="color:white;margin:0;">⚠️ You're Almost Out of Documents</h1>
      </div>
      <div style="padding:30px;">
        <p>Hi <strong>{name}</strong>,</p>
        <p>You've used <strong>{used} of your {limit} free documents</strong> this month.</p>
        <p>Upgrade to <strong>Pro (₦4,999/month)</strong> for unlimited documents, PDF downloads, and professional formatting — no watermarks.</p>
        <p>Open Telegram and type <strong>/upgrade</strong> to continue without interruption.</p>
      </div>
    </div>
    """
    return await send_email(to, "BizPilot NG — Running Low on Documents", html)
