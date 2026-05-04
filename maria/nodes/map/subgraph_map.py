import sys
import os
from langgraph.graph import StateGraph, END
from nodes.map.subnodes.generate import GenerateMNode
from nodes.map.subnodes.validate import ValidateMNode
from nodes.map.subnodes.fix import FixMNode
from state.agent_state import MState

ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
ruta_prompt = os.path.join(ruta_raiz, "prompts", "promptMap.txt")

def build_map_subgraph(llm):
    gen_node = GenerateMNode(llm, ruta_prompt)
    val_node = ValidateMNode()
    fix_node = FixMNode(llm)

    workflow = StateGraph(MState)

    workflow.add_node("generate", gen_node)
    workflow.add_node("validate", val_node)
    workflow.add_node("fix", fix_node)

    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "validate")

    def should_continue(state: MState):
        if state["validated"]:
            return END
        if state["retries"] >= 3:
            return END
        return "fix"

    workflow.add_conditional_edges("validate", should_continue, {END: END, "fix": "fix"})
    workflow.add_edge("fix", "validate")

    return workflow.compile()