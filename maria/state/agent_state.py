from typing import TypedDict, Optional

# ==========================================
# 1. ESTADOS DE LOS EQUIPOS (Sub-grafos)
# ==========================================
# Estos son los estados que usan los nodos generate, validate y fix por dentro.
# Cada equipo tiene sus propios reintentos y errores.

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
    initial_idea:str
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
# 2. Grafo Maestro
# ==========================================


class MasterState(TypedDict):
    problem_definition: str
    target_user: str
    pain_points: str
    initial_idea: str
    prefered_goal: Optional[str]
    ltg_analysis: Optional[dict]
    final_sq: Optional[dict]
    map_schema: Optional[dict]
    final_hmw: Optional[dict]
    map_code: Optional[str]
    
    is_approved: bool