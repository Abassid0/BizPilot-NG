"""
app/services/ai/claude_client.py
---------------------------------
Anthropic Claude API wrapper.

Responsibilities:
- Make the API call with proper error handling
- Parse the structured JSON response
- Retry on transient failures (rate limits, timeouts)
- Track token usage for cost monitoring
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import anthropic

from app.core.config import settings
from app.core.constants import DocType
from app.services.ai.prompts import get_prompt_builder


# ── Client Singleton ─────────────────────────────────────────────────────────

_client: Optional[anthropic.AsyncAnthropic] = None


def get_claude_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        kwargs: dict = {"api_key": settings.anthropic_api_key}
        if settings.anthropic_base_url:
            kwargs["base_url"] = settings.anthropic_base_url
        _client = anthropic.AsyncAnthropic(**kwargs)
    return _client


# ── Core Generation Function ─────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
)
async def generate_document(
    doc_type: DocType,
    user_data: dict,
    business_profile: dict,
) -> dict[str, Any]:
    """
    Generate a structured document using Claude.

    Returns:
        {
            "success": True/False,
            "data": { ...parsed JSON from Claude... },
            "raw_text": "...",
            "tokens_used": { "input": N, "output": N },
            "error": "..." (only if success=False)
        }
    """
    client = get_claude_client()

    merged_data = {**business_profile, **user_data}

    prompt_builder = get_prompt_builder(doc_type)
    system_prompt, user_prompt = prompt_builder(merged_data)

    logger.info(f"Generating {doc_type} document for user data keys: {list(merged_data.keys())}")

    try:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
        )

        raw_text = response.content[0].text.strip()
        tokens = {
            "input":  response.usage.input_tokens,
            "output": response.usage.output_tokens,
        }

        logger.info(
            f"Claude responded | doc_type={doc_type} | "
            f"tokens={tokens['input']}+{tokens['output']}"
        )

        parsed = _parse_json_response(raw_text)
        if parsed is None:
            return {
                "success":     False,
                "data":        {},
                "raw_text":    raw_text,
                "tokens_used": tokens,
                "error":       "Failed to parse Claude response as JSON",
            }

        return {
            "success":     True,
            "data":        parsed,
            "raw_text":    raw_text,
            "tokens_used": tokens,
        }

    except anthropic.AuthenticationError as e:
        logger.error(f"Claude auth error: {e}")
        return {"success": False, "data": {}, "raw_text": "", "tokens_used": {}, "error": "AI service authentication failed"}

    except anthropic.RateLimitError:
        raise

    except anthropic.APIConnectionError:
        raise

    except Exception as e:
        logger.error(f"Unexpected Claude error: {e}")
        return {
            "success":     False,
            "data":        {},
            "raw_text":    "",
            "tokens_used": {},
            "error":       f"Document generation failed: {str(e)}",
        }


async def transcribe_voice(audio_bytes: bytes, file_ext: str = "ogg") -> Optional[str]:
    """
    Transcribe a voice message using OpenAI Whisper.
    Returns the transcribed text, or None on failure.

    Telegram sends voice messages as .ogg (Opus codec).
    Whisper auto-detects language — supports English, Pidgin, Yoruba, Igbo, Hausa.
    """
    if not settings.openai_api_key:
        logger.warning("OpenAI API key not set — voice transcription unavailable")
        return None

    try:
        import openai
        client = openai.OpenAI(api_key=settings.openai_api_key)

        import io
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"voice.{file_ext}"

        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
        logger.info(f"Whisper transcription: {transcript.text[:80]}...")
        return transcript.text

    except Exception as e:
        logger.error(f"Voice transcription error: {e}")
        return None


# ── JSON Parsing Helper ──────────────────────────────────────────────────────

def _parse_json_response(text: str) -> Optional[dict]:
    """
    Extract and parse JSON from Claude's response.
    Claude sometimes wraps JSON in markdown code fences — we strip those.
    Uses json.JSONDecoder.raw_decode to find the first complete JSON object
    instead of a greedy regex that could merge multiple objects.
    """
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = text.rstrip("`").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    try:
        decoder = json.JSONDecoder()
        idx = text.index("{")
        result, _ = decoder.raw_decode(text, idx)
        if isinstance(result, dict):
            return result
    except (ValueError, json.JSONDecodeError):
        pass

    logger.warning(f"Could not parse JSON from Claude response. First 200 chars: {text[:200]}")
    return None


# ── Cost Estimation Utility ──────────────────────────────────────────────────

def estimate_cost_naira(
    input_tokens: int,
    output_tokens: int,
    usd_to_naira: float = 1_600.0,
) -> float:
    """
    Approximate cost in Naira for a Claude Sonnet 4 call.
    Pricing: $3/M input, $15/M output. Pass current USD/NGN rate for accuracy.
    """
    usd_cost = (input_tokens / 1_000_000) * 3.0 + (output_tokens / 1_000_000) * 15.0
    return round(usd_cost * usd_to_naira, 2)
