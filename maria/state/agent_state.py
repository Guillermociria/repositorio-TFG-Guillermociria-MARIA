from typing import TypedDict, Optional

# ==========================================
# 1. ESTADOS DE LOS EQUIPOS (Sub-grafos)
# ==========================================
# Estos son los estados que usan los nodos generate, validate y fix por dentro.
# Cada equipo tiene sus propios reintentos y errores.

class LTGState(TypedDict):
    # Inputs que necesita el equipo LTG
    problem_definition: str
    target_user: str
    pain_points: str
    initial_idea: str
    
    # Variables de control técnico (Aisladas aquí)
    validated: bool  
    retries: int
    errors: Optional[str]
    raw_output: Optional[str]
    
    # El tesoro final que devolverán
    ltg_analysis: Optional[dict]

class SQState(TypedDict):
    # Inputs que necesita el equipo de Sprint Questions (SQ)
    ltg_analysis: dict
    prefered_goal: str
    
    # Variables de control técnico (Aisladas aquí)
    validated: bool  
    retries: int
    errors: Optional[str]
    raw_output: Optional[str]
    
    # El tesoro final que devolverán
    sprint_questions: Optional[dict]


# ==========================================
# 2. EL ESTADO DEL JEFE (Grafo Maestro)
# ==========================================
# Este es el estado que recibe tu aplicación web Django.
# Está limpio de reintentos y basura técnica. Solo tiene la entrada del usuario y los resultados.

class MasterState(TypedDict):
    # Entradas originales del usuario
    problem_definition: str
    target_user: str
    pain_points: str
    initial_idea: str
    prefered_goal: Optional[str] # Lo rellenará el usuario más adelante en la interfaz
    
    # Resultados Finales Validados (Las "Cajas Fuertes")
    # Al principio son None. Los sub-grafos las irán rellenando cuando terminen su trabajo.
    ltg_analysis: Optional[dict]
    final_sq: Optional[dict]
    final_hmw: Optional[dict] # Para el futuro equipo How Might We