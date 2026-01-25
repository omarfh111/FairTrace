"""
Agents Package

Contains all credit decision agents:
- BaseAgent: Abstract base class
- RiskAgent: The Prosecutor - finds reasons to reject
- FairnessAgent: The Advocate - ensures equitable treatment
- TrajectoryAgent: The Predictor - forecasts future outcomes
- Orchestrator: Synthesizes verdicts into final decision
- AdvisorAgent: The Counselor - provides improvement recommendations (on-demand)
- NarrativeAgent: The Storyteller - extracts insights from historical cases (on-demand)
- ComparatorAgent: The Analyst - gap analysis vs. successful cases (on-demand)
- ScenarioAgent: The Strategist - what-if scenario modeling (on-demand)
"""

from .base_agent import BaseAgent
from .risk_agent import RiskAgent
from .fairness_agent import FairnessAgent
from .trajectory_agent import TrajectoryAgent
from .orchestrator import Orchestrator
from .advisor_agent import AdvisorAgent
from .narrative_agent import NarrativeAgent
from .comparator_agent import ComparatorAgent
from .scenario_agent import ScenarioAgent

__all__ = [
    "BaseAgent",
    "RiskAgent",
    "FairnessAgent",
    "TrajectoryAgent",
    "Orchestrator",
    "AdvisorAgent",
    "NarrativeAgent",
    "ComparatorAgent",
    "ScenarioAgent"
]
