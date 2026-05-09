from app.agents.base import BaseAgent

SYSTEM_PROMPT = "You are the Publishing Agent for Sovereign. You execute approved assets to social channels."


class PublishingAgent(BaseAgent):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[])
