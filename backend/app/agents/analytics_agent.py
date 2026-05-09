from app.agents.base import BaseAgent

SYSTEM_PROMPT = "You are the Analytics Agent for Sovereign."


class AnalyticsAgent(BaseAgent):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[])
