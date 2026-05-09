from app.agents.base import BaseAgent

SYSTEM_PROMPT = "You are the Design Agent for Sovereign. You generate professional marketing visuals using fal.ai."


class DesignAgent(BaseAgent):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[])
