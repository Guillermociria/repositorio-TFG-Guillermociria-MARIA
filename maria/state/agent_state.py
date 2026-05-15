from typing import TypedDict, Optional, List


# ==========================================
# 1. ESTADOS DE LOS SUBGRAFOS
# ==========================================

class LTGState(TypedDict):
    problem_definition: str
    target_user: str
    pain_points: str
    initial_idea: str

    validated: bool
    retries: int
    errors: Optional[str]
    raw_output: Optional[str]

    ltg_analysis: Optional[dict]


class SQState(TypedDict):
    problem_definition: str
    ltg_analysis: dict
    prefered_goal: str
    initial_idea: str

    validated: bool
    retries: int
    errors: Optional[str]
    raw_output: Optional[str]

    final_sq: Optional[dict]


class MState(TypedDict):
    problem_definition: str
    ltg_analysis: dict
    prefered_goal: str
    initial_idea: str
    final_sq: Optional[dict]

    validated: bool
    retries: int
    errors: Optional[str]
    raw_output: Optional[str]

    map_schema: Optional[dict]


class GMState(TypedDict):
    map_schema: dict

    validated: bool
    retries: int
    errors: Optional[str]
    raw_output: Optional[str]

    map_code: Optional[str]


# ==========================================
# 2. ESTADO DEL GRAFO MAESTRO
# ==========================================

class MasterState(TypedDict):
    problem_definition: str
    target_user: str
    pain_points: str
    initial_idea: str

    selected_techniques: List[str]   
    technique_prompts: dict        
    current_technique_index: int     

    technique_outputs: dict        

    technique_extra_inputs: dict 

    technique_llm_providers: dict
    user_api_keys: dict

    language: str 

    is_approved: bool
    user_feedback: str