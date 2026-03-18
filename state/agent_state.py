from typing import TypedDict, List

class AgentState(TypedDict):
    context: str
    long_term_goal: str
    is_goal_valid: bool
    sprint_questions: List[str]  # Los riesgos refinados
    hmw_list: List[str]          # Los retos generados
    selected_hmw: str            # El ganador tras la votación
    prototype_html: str          # El código final