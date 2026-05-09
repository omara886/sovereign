from app.agents.base import BaseAgent

SYSTEM_PROMPT = "You are the Strategy Agent for Sovereign, an autonomous AI marketing command center."


class StrategyAgent(BaseAgent):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[])
