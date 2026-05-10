"""
Base agent — supports both Anthropic and DeepSeek.
Model routing:
  Sonnet   → Strategy, Brand, Copy, Analytics (complex reasoning + Arabic quality)
  DeepSeek → QA, Localization, Design prompts (10x cheaper, fast, good enough)
Prompt caching on Anthropic saves ~90% on repeated system prompt tokens.
"""
import asyncio
import json
import logging

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings

logger = logging.getLogger(__name__)

# Anthropic
SONNET = "claude-sonnet-4-20250514"
HAIKU  = "claude-haiku-4-5-20251001"

# DeepSeek — OpenAI-compatible, ~10x cheaper than Sonnet
DEEPSEEK = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class BaseAgent:
    MODEL = SONNET

    def __init__(self, system_prompt: str, tools: list, max_tokens: int = 4096):
        settings = get_settings()
        self.system_prompt = system_prompt
        self.tools = tools
        self.max_tokens = max_tokens
        self.tool_implementations: dict = {}
        self._anthropic = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._deepseek_key = settings.DEEPSEEK_API_KEY

    def _is_deepseek(self) -> bool:
        return self.MODEL == DEEPSEEK

    async def run(self, user_message: str, db: AsyncSession) -> str:
        if self._is_deepseek():
            return await self._run_deepseek(user_message)
        return await self._run_anthropic(user_message, db)

    # ── Anthropic (tool-use capable) ──────────────────────────────────────────
    async def _run_anthropic(self, user_message: str, db: AsyncSession) -> str:
        messages = [{"role": "user", "content": user_message}]
        system_with_cache = [{"type": "text", "text": self.system_prompt, "cache_control": {"type": "ephemeral"}}]

        for _ in range(12):
            response = await self._anthropic_create(system_with_cache, messages)

            if response.stop_reason == "end_turn":
                for block in reversed(response.content):
                    if getattr(block, "type", None) == "text":
                        return block.text
                return ""

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if getattr(block, "type", None) == "tool_use":
                        fn = self.tool_implementations.get(block.name)
                        try:
                            result = await fn(db=db, **block.input) if fn else {"error": f"tool {block.name} not found"}
                        except Exception as exc:
                            result = {"error": str(exc)}
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result, default=str)})
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

        raise RuntimeError("agent loop limit (12) reached")

    async def _anthropic_create(self, system: list, messages: list, max_retries: int = 4):
        for attempt in range(max_retries):
            try:
                return await self._anthropic.messages.create(
                    model=self.MODEL,
                    max_tokens=self.max_tokens,
                    system=system,
                    tools=self.tools if self.tools else [],
                    messages=messages,
                    extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
                )
            except anthropic.RateLimitError as e:
                if attempt == max_retries - 1:
                    raise
                wait = 20 * (2 ** attempt)
                logger.warning("Anthropic rate limit (attempt %d/%d) — waiting %ds", attempt + 1, max_retries, wait)
                await asyncio.sleep(wait)
            except anthropic.APIStatusError as e:
                if e.status_code == 529 and attempt < max_retries - 1:
                    await asyncio.sleep(10 * (attempt + 1))
                    continue
                raise

    # ── DeepSeek (OpenAI-compatible, no tool-use needed for simple tasks) ─────
    async def _run_deepseek(self, user_message: str) -> str:
        if not self._deepseek_key:
            logger.warning("DEEPSEEK_API_KEY not set — falling back to Haiku")
            # Fallback: call Anthropic with Haiku
            self.MODEL = HAIKU
            class FakeDb:
                pass
            return await self._run_anthropic(user_message, FakeDb())  # type: ignore

        import httpx
        for attempt in range(4):
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        f"{DEEPSEEK_BASE_URL}/chat/completions",
                        headers={"Authorization": f"Bearer {self._deepseek_key}", "Content-Type": "application/json"},
                        json={
                            "model": "deepseek-chat",
                            "messages": [
                                {"role": "system", "content": self.system_prompt},
                                {"role": "user", "content": user_message},
                            ],
                            "max_tokens": self.max_tokens,
                            "temperature": 0.7,
                        },
                    )
                    if resp.status_code == 429 and attempt < 3:
                        await asyncio.sleep(15 * (attempt + 1))
                        continue
                    resp.raise_for_status()
                    return resp.json()["choices"][0]["message"]["content"]
            except Exception as exc:
                if attempt == 3:
                    raise RuntimeError(f"DeepSeek failed: {exc}") from exc
                await asyncio.sleep(10)
        return ""
