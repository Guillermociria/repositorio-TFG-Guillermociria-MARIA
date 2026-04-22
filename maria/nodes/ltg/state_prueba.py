from typing import TypedDict, Optional, List

class AgentState(TypedDict):
    problem_definition: str
    target_user: str
    pain_points: str
    initial_idea: str
    raw_output: Optional[str]
    ltg_analysis: Optional[dict]
    errors: Optional[str]
    retries: int
    prefered_goal: Optional[str]
    validated: bool