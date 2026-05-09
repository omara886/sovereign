from app.agents.base import BaseAgent

SYSTEM_PROMPT = "You are the Brand Agent for Sovereign. You build and maintain the authoritative brand identity for each project."


class BrandAgent(BaseAgent):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[])
