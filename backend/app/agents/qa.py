from app.agents.base import BaseAgent

SYSTEM_PROMPT = "You are the QA Agent for Sovereign. Nothing reaches the founder's approval inbox until it passes all your checks."


class QAAgent(BaseAgent):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[])
