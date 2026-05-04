import sys
import os
from langgraph.graph import StateGraph, END
from nodes.generate_map.subnodes.generate import GenerateGMNode
from nodes.generate_map.subnodes.validate import ValidateMermaidNode
from nodes.generate_map.subnodes.fix import FixGMNode
from state.agent_state import GMState

ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
ruta_prompt = os.path.join(ruta_raiz, "prompts", "promptGenerateMap.txt")

def build_generate_map_subgraph(llm):
    gen_node = GenerateGMNode(llm, ruta_prompt)
    val_node = ValidateMermaidNode()
    fix_node = FixGMNode(llm)

    workflow = StateGraph(GMState)

    workflow.add_node("generate", gen_node)
    workflow.add_node("validate", val_node)
    workflow.add_node("fix", fix_node)

    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "validate")

    def should_continue(state: GMState):
        if state["validated"]:
            return END
        if state["retries"] >= 3:
            return END
        return "fix"

    workflow.add_conditional_edges("validate", should_continue, {END: END, "fix": "fix"})
    workflow.add_edge("fix", "validate")

    return workflow.compile()