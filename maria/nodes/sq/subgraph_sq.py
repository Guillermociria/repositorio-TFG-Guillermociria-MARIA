import sys
import os
from langgraph.graph import StateGraph, END
from nodes.sq.subnodes.generate import GenerateSQNode
from nodes.sq.subnodes.validate import ValidateSQNode
from nodes.sq.subnodes.fix import FixSQNode
from state.agent_state import SQState

ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
ruta_prompt = os.path.join(ruta_raiz, "prompts", "promptSprintQuestions.txt")

def build_sq_subgraph(llm):
    gen_node = GenerateSQNode(llm, ruta_prompt)
    val_node = ValidateSQNode()
    fix_node = FixSQNode(llm)

    workflow = StateGraph(SQState)

    workflow.add_node("generate", gen_node)
    workflow.add_node("validate", val_node)
    workflow.add_node("fix", fix_node)

    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "validate")

    def should_continue(state: SQState):
        if state["validated"]:
            return END
        if state["retries"] >= 3:
            return END
        return "fix"

    workflow.add_conditional_edges("validate", should_continue, {END: END, "fix": "fix"})
    workflow.add_edge("fix", "validate")

    return workflow.compile()