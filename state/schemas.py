from typing import TypedDict, List, Dict

class LTGAnalysis(TypedDict):
    critique: str
    assumptions: List[str]
    alternatives: Dict[str, str]
    risks: List[str]

class HMWAnalysis(TypedDict):
    failure_scenario: str
    user_skepticism: List[str]
    expert_cynicism: List[str]
    fatal_flaw: str