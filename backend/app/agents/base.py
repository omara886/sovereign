"""
Base agent with:
- Model routing: Sonnet for complex reasoning, Haiku for structured/cheap tasks
- Prompt caching: system prompt cached on every call (saves ~90% on repeated runs)
- Tool-use loop: runs until end_turn or 12 iterations
"""
import asyncio
import json
import logging

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings

logger = logging.getLogger(__name__)

# Model constants — change here to update everywhere
SONNET = "claude-sonnet-4-20250514"   # Strategy, Brand, Copy, Analytics
HAIKU = "claude-haiku-4-5-20251001"   # QA, Localization, Design (cheap + fast)


class BaseAgent:
    MODEL = SONNET  # subclasses override

    def __init__(self, system_prompt: str, tools: list, max_tokens: int = 4096):
        self.client = anthropic.AsyncAnthropic(api_key=get_settings().ANTHROPIC_API_KEY)
        self.system_prompt = system_prompt
        self.tools = tools
        self.max_tokens = max_tokens
        self.tool_implementations: dict = {}

    async def run(self, user_message: str, db: AsyncSession) -> str:
        messages = [{"role": "user", "content": user_message}]

        # Prompt caching: mark system prompt as cacheable
        # Anthropic caches blocks ≥1024 tokens for 5 minutes — saves ~90% on tokens
        system_with_cache = [
            {
                "type": "text",
                "text": self.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        for _ in range(12):
            response = await self._create_with_retry(system_with_cache, messages)

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
                        if fn is None:
                            result = {"error": f"tool {block.name} not implemented"}
                        else:
                            try:
                                result = await fn(db=db, **block.input)
                            except Exception as exc:
                                result = {"error": str(exc)}
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, default=str),
                        })
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

        raise RuntimeError("agent loop limit reached after 12 iterations")

    async def _create_with_retry(self, system: list, messages: list, max_retries: int = 4) -> anthropic.types.Message:
        """Retry on rate limit errors with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return await self.client.messages.create(
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
                wait = 20 * (2 ** attempt)  # 20s, 40s, 80s, 160s
                logger.warning("Rate limit hit (attempt %d/%d) — waiting %ds: %s", attempt + 1, max_retries, wait, str(e)[:80])
                await asyncio.sleep(wait)
            except anthropic.APIStatusError as e:
                if e.status_code == 529 and attempt < max_retries - 1:  # overloaded
                    await asyncio.sleep(10 * (attempt + 1))
                    continue
                raise
