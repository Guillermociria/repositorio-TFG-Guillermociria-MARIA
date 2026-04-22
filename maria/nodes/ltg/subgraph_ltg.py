import sys
import os
from langgraph.graph import StateGraph, END
from nodes.ltg.subnodes.generate import GenerateLTGNode
from nodes.ltg.subnodes.validate import ValidateLTGNode
from nodes.ltg.subnodes.fix import FixLTGNode
from state.agent_state import LTGState

ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
ruta_prompt = os.path.join(ruta_raiz, "prompts", "promptLongTermGoalReduced.txt")

def build_ltg_subgraph(llm):
    gen_node = GenerateLTGNode(llm, ruta_prompt)
    val_node = ValidateLTGNode()
    fix_node = FixLTGNode(llm)

    workflow = StateGraph(LTGState)

    workflow.add_node("generate", gen_node)
    workflow.add_node("validate", val_node)
    workflow.add_node("fix", fix_node)

    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "validate")

    def should_continue(state: LTGState):
        if state["validated"]:
            return END
        if state["retries"] >= 3:
            return END
        return "fix"

    workflow.add_conditional_edges("validate", should_continue, {END: END, "fix": "fix"})
    workflow.add_edge("fix", "validate")

    return workflow.compile()