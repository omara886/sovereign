from app.agents.base import BaseAgent

SYSTEM_PROMPT = "You are the Localization Agent for Sovereign. You produce native-quality Arabic and English marketing content."


class LocalizationAgent(BaseAgent):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[])
