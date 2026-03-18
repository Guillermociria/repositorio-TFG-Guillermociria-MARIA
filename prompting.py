from typing import TypedDict, List, Dict, Optional

class LTGAnalysis(TypedDict):
    critique: str
    assumptions: List[str]
    alternatives: Dict[str, str]
    risks: List[str]

class PreMortem(TypedDict):
    failure_scenario: str
    user_skepticism: List[str]
    expert_cynicism: List[str]
    fatal_flaw: str

class AgentState(TypedDict):
    # INPUT
    problem_definition: str
    target_user: str
    pain_points: str
    initial_idea: str
    
    # OUTPUTS
    ltg_analysis: Optional[LTGAnalysis]
    pre_mortem: Optional[PreMortem]
    
    # CONTROL
    raw_output: Optional[str]
    parsed_output: Optional[dict]
    validated: bool
    errors: Optional[str]
    
    retries: int
    max_retries: int
    
def load_prompt(path: str) -> str:
    with open(path, "r") as f:
        return f.read()
    
def generate_ltg_analysis(state: AgentState):
    template = load_prompt("prompts/ltg.txt")
    
    prompt = template.format(
        ProblemDefinition=state["problem_definition"],
        TargetUser=state["target_user"],
        PainPoints=state["pain_points"],
        InitialIdea=state["initial_idea"]
    )
    
    response = llm.invoke(prompt)
    
    return {
        **state,
        "raw_output": response.content
    }
    
import json

def validate_ltg(state: AgentState):
    try:
        data = json.loads(state["raw_output"])
    except:
        return {**state, "validated": False, "errors": "invalid_json"}
    
    required = ["critique", "assumptions", "alternatives", "risks"]
    
    for key in required:
        if key not in data:
            return {
                **state,
                "validated": False,
                "errors": f"missing_{key}"
            }
    
    return {
        **state,
        "validated": True,
        "ltg_analysis": data
    }
    

def fix_ltg(state: AgentState):
    fix_prompt = f"""
    Tu output anterior es inválido.
    
    ERROR: {state['errors']}
    
    OUTPUT:
    {state['raw_output']}
    
    Corrige y devuelve SOLO JSON válido con:
    critique, assumptions, alternatives, risks
    """
    
    response = llm.invoke(fix_prompt)
    
    return {
        **state,
        "raw_output": response.content,
        "retries": state["retries"] + 1
    }
    
    
def route_validation(state: AgentState):
    if state["validated"]:
        return "next"
    
    if state["retries"] >= state["max_retries"]:
        return "fallback"
    
    return "fix"

def generate_pre_mortem(state: AgentState):
    template = load_prompt("prompts/pre_mortem.txt")
    
    prompt = template.format(
        context=state["problem_definition"],
        ltg=state["ltg_analysis"]
    )
    
    response = llm.invoke(prompt)
    
    return {
        **state,
        "raw_output": response.content,
        "validated": False,
        "retries": 0
    }
    
def validate_pre_mortem(state: AgentState):
    try:
        data = json.loads(state["raw_output"])
    except:
        return {**state, "validated": False, "errors": "invalid_json"}
    
    required = [
        "failure_scenario",
        "user_skepticism",
        "expert_cynicism",
        "fatal_flaw"
    ]
    
    for key in required:
        if key not in data:
            return {
                **state,
                "validated": False,
                "errors": f"missing_{key}"
            }
    
    return {
        **state,
        "validated": True,
        "pre_mortem": data
    }
    
    
def fix_pre_mortem(state: AgentState):
    fix_prompt = f"""
    El pre-mortem no cumple formato.
    
    ERROR: {state['errors']}
    
    OUTPUT:
    {state['raw_output']}
    
    Devuelve SOLO JSON válido con:
    failure_scenario, user_skepticism, expert_cynicism, fatal_flaw
    """
    
    response = llm.invoke(fix_prompt)
    
    return {
        **state,
        "raw_output": response.content,
        "retries": state["retries"] + 1
    }
    
    
def fallback(state: AgentState):
    return {
        **state,
        "errors": "max_retries_exceeded"
    }
    
def end(state: AgentState):
    return state

from langgraph.graph import StateGraph

graph = StateGraph(AgentState)

# Nodos
graph.add_node("generate_ltg", generate_ltg_analysis)
graph.add_node("validate_ltg", validate_ltg)
graph.add_node("fix_ltg", fix_ltg)

graph.add_node("generate_pm", generate_pre_mortem)
graph.add_node("validate_pm", validate_pre_mortem)
graph.add_node("fix_pm", fix_pre_mortem)

graph.add_node("fallback", fallback)
graph.add_node("end", end)

# Entry
graph.set_entry_point("generate_ltg")

# Flujo LTG
graph.add_edge("generate_ltg", "validate_ltg")

graph.add_conditional_edges(
    "validate_ltg",
    route_validation,
    {
        "next": "generate_pm",
        "fix": "fix_ltg",
        "fallback": "fallback"
    }
)

graph.add_edge("fix_ltg", "validate_ltg")

# Flujo Pre-Mortem
graph.add_edge("generate_pm", "validate_pm")

graph.add_conditional_edges(
    "validate_pm",
    route_validation,
    {
        "next": "end",
        "fix": "fix_pm",
        "fallback": "fallback"
    }
)

graph.add_edge("fix_pm", "validate_pm")