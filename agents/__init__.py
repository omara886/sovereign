from pathlib import Path
import sys

_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if _BACKEND_DIR.exists():
    backend_path = str(_BACKEND_DIR)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

from app.agents.analytics_agent import AnalyticsAgent
from app.agents.approval_agent import ApprovalAgent
from app.agents.copy import CopyAgent
from app.agents.design import DesignAgent
from app.agents.localization import LocalizationAgent
from app.agents.qa import QAAgent
from app.agents.publishing import PublishingAgent
from app.agents.strategy import StrategyAgent

__all__ = [
    "AnalyticsAgent",
    "ApprovalAgent",
    "CopyAgent",
    "DesignAgent",
    "LocalizationAgent",
    "QAAgent",
    "PublishingAgent",
    "StrategyAgent",
]
