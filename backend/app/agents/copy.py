from app.agents.base import BaseAgent

SYSTEM_PROMPT = "You are the Copy Agent for Sovereign. You write high-converting marketing copy in Arabic and English."


class CopyAgent(BaseAgent):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[])
