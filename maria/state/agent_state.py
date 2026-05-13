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
    # Contexto base del problema
    problem_definition: str
    target_user: str
    pain_points: str
    initial_idea: str

    # Pipeline configurado por el usuario
    selected_techniques: List[str]   # IDs ordenados: ["ltg", "hmw", "brainstorming"]
    technique_prompts: dict          # technique_id -> prompt personalizado (opcional)
    current_technique_index: int     # índice de la técnica en ejecución

    # Outputs acumulados. Al ejecutar la técnica N, las claves 0..N-1
    # ya están aquí y se pasan como contexto adicional.
    technique_outputs: dict          # {"ltg": {...}, "hmw": {...}, ...}

    # Inputs adicionales por técnica (cuestionario previo)
    technique_extra_inputs: dict   # {"ltg": {"focus": "..."}, ...}

    # LLM selection per technique
    technique_llm_providers: dict  # {"ltg": "google", "hmw": "openai", ...}
    user_api_keys: dict            # {"google": "...", "openai": "...", "anthropic": "..."}

    # Control HITL
    is_approved: bool
    user_feedback: str