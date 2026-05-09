import json

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession


class BaseAgent:
    MODEL = "claude-sonnet-4-20250514"

    def __init__(self, system_prompt: str, tools: list, max_tokens: int = 4096):
        self.client = anthropic.AsyncAnthropic()
        self.system_prompt = system_prompt
        self.tools = tools
        self.max_tokens = max_tokens
        self.tool_implementations = {}

    async def run(self, user_message: str, db: AsyncSession) -> str:
        messages = [{"role": "user", "content": user_message}]
        for _ in range(12):
            response = await self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                tools=self.tools,
                messages=messages,
            )
            if response.stop_reason == "end_turn":
                for block in reversed(response.content):
                    if getattr(block, "type", None) == "text":
                        return block.text
                return ""
            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if getattr(block, "type", None) == "tool_use":
                        fn = self.tool_implementations[block.name]
                        result = await fn(db=db, **block.input)
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result, default=str)})
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
        raise RuntimeError("agent loop limit reached")
