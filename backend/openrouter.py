"""OpenRouter client with fallback chain across multiple cheap models."""

import json
import logging
import re
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

FALLBACK_MODELS = [
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.1-8b-instruct",
    "mistralai/mistral-7b-instruct",
    "google/gemma-2-9b-it",
    "qwen/qwen-2.5-7b-instruct",
]

SYSTEM_PROMPT = """You are an expert at analyzing student survey responses and extracting key themes.

Given a list of student responses to a question, extract exactly 4 to 6 major themes.

For each theme, provide:
- "title": A short title (3-5 words)
- "description": A 1-2 sentence description of the theme
- "student_names": A list of student names whose answers relate to this theme

A single student can appear in multiple themes if their answer touches on multiple topics.

You MUST respond with valid JSON only. No markdown, no explanation, no code fences. Just the JSON object.

Response format:
{"themes": [{"title": "...", "description": "...", "student_names": ["..."]}, ...]}"""


def _build_user_prompt(question: str, responses: list[dict]) -> str:
    """Build the user prompt from question and student responses."""
    lines = [f'Question asked: "{question}"\n', "Student responses:"]
    for i, r in enumerate(responses, 1):
        lines.append(f'{i}. {r["student_name"]}: "{r["answer"]}"')
    return "\n".join(lines)


def _parse_themes_json(text: str) -> Optional[dict]:
    """Try to parse themes from LLM response text. Falls back to regex extraction."""
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    # Attempt 1: direct JSON parse
    try:
        data = json.loads(cleaned)
        if "themes" in data and isinstance(data["themes"], list):
            return data
    except json.JSONDecodeError:
        pass

    # Attempt 2: find JSON object with regex
    match = re.search(r"\{[\s\S]*\"themes\"\s*:\s*\[[\s\S]*\]\s*\}", cleaned)
    if match:
        try:
            data = json.loads(match.group(0))
            if "themes" in data and isinstance(data["themes"], list):
                return data
        except json.JSONDecodeError:
            pass

    # Attempt 3: try to find array of themes directly
    match = re.search(r"\[[\s\S]*\]", cleaned)
    if match:
        try:
            arr = json.loads(match.group(0))
            if isinstance(arr, list) and len(arr) > 0 and "title" in arr[0]:
                return {"themes": arr}
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse themes from LLM response: %s", text[:200])
    return None


async def summarize_responses(
    question: str,
    responses: list[dict],
    api_key: Optional[str] = None,
) -> Optional[dict]:
    """Call OpenRouter with fallback chain to summarize student responses.

    Returns dict with 'themes' list and 'model_used', or None if all models fail.
    """
    api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.error("OPENROUTER_API_KEY not set")
        return None

    user_prompt = _build_user_prompt(question, responses)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://themepulse.app",
        "X-Title": "ThemePulse",
    }

    for model_id in FALLBACK_MODELS:
        try:
            logger.info("Trying model: %s", model_id)
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            }

            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                )

            if resp.status_code != 200:
                logger.warning(
                    "Model %s returned status %d: %s",
                    model_id, resp.status_code, resp.text[:200],
                )
                continue

            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            if not content:
                logger.warning("Model %s returned empty content", model_id)
                continue

            parsed = _parse_themes_json(content)
            if parsed is None:
                logger.warning("Model %s returned unparseable content", model_id)
                continue

            # Validate themes structure
            themes = parsed.get("themes", [])
            valid_themes = []
            for t in themes:
                if isinstance(t, dict) and "title" in t and "description" in t:
                    valid_themes.append({
                        "title": str(t.get("title", "")),
                        "description": str(t.get("description", "")),
                        "student_names": [
                            str(n) for n in t.get("student_names", [])
                            if isinstance(n, str)
                        ],
                    })

            if len(valid_themes) < 2:
                logger.warning("Model %s returned too few valid themes: %d", model_id, len(valid_themes))
                continue

            logger.info("Successfully used model: %s (%d themes)", model_id, len(valid_themes))
            return {
                "themes": valid_themes,
                "model_used": model_id,
            }

        except httpx.TimeoutException:
            logger.warning("Model %s timed out", model_id)
            continue
        except Exception as e:
            logger.warning("Model %s failed with error: %s", model_id, str(e))
            continue

    logger.error("All models failed to produce a valid summary")
    return None
