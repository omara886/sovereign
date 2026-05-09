from app.agents.base import BaseAgent

SYSTEM_PROMPT = "You are the Approval Agent for Sovereign. You route QA-passed items to the founder and handle all approval logistics."


class ApprovalAgent(BaseAgent):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[])
