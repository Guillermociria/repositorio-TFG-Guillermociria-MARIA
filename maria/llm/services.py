# maria/llm/services.py
import os
import atexit
from psycopg_pool import ConnectionPool
from nodes.llm import get_compiled_master_graph

DB_URI = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

_pool = None

def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(conninfo=DB_URI, max_size=20, kwargs={"autocommit": True})
        atexit.register(_pool.close)
    return _pool


def get_session_state(thread_id):
    """Returns current LangGraph state for a thread, or None if no checkpoint exists."""
    try:
        app    = get_compiled_master_graph(get_pool())
        config = {"configurable": {"thread_id": thread_id}}
        estado = app.get_state(config)
        if not estado or not estado.values:
            return None
        values     = estado.values
        next_nodes = estado.next
        siguiente  = next_nodes[0] if next_nodes else "END"

        idx        = values.get("current_technique_index", 0)
        selected   = values.get("selected_techniques", [])
        outputs    = values.get("technique_outputs", {})
        current_id = selected[idx] if idx < len(selected) else None
        output     = outputs.get(current_id) if current_id else None

        awaiting_pre_inputs = (
            siguiente == "run_technique"
            and current_id is not None
            and current_id not in outputs
        )

        return {
            "estado":               siguiente,
            "current_index":        idx,
            "technique_id":         current_id,
            "output":               output,
            "all_outputs":          outputs,
            "awaiting_pre_inputs":  awaiting_pre_inputs,
            "selected_techniques":  selected,
            "problem_definition":   values.get("problem_definition", ""),
            "target_user":          values.get("target_user", ""),
            "pain_points":          values.get("pain_points", ""),
            "initial_idea":         values.get("initial_idea", ""),
        }
    except Exception:
        return None


def ejecutar_agente_sprint(thread_id, inputs=None, feedback=None, action=None,
                           extra_inputs=None, current_prompt=None):
    """
    Puente entre Django y LangGraph.
    action: 'start' | 'pre_inputs' | 'approve' | 'feedback'
    """
    app    = get_compiled_master_graph(get_pool())
    config = {"configurable": {"thread_id": thread_id}}

    if action == "start" and inputs:
        # Pre-load default prompts for custom (non-registry) techniques
        from nodes.llm import TECHNIQUE_REGISTRY
        from llm.models import Technique
        for tid in inputs.get("selected_techniques", []):
            if tid not in TECHNIQUE_REGISTRY and tid not in inputs.get("technique_prompts", {}):
                try:
                    tech = Technique.objects.get(tech_id=tid)
                    inputs.setdefault("technique_prompts", {})[tid] = tech.default_prompt
                except Technique.DoesNotExist:
                    pass
        app.invoke(inputs, config)

    elif action == "pre_inputs":
        estado = app.get_state(config)
        idx    = estado.values.get("current_technique_index", 0)
        sel    = estado.values.get("selected_techniques", [])
        tech_id = sel[idx] if idx < len(sel) else None

        update = {}
        if tech_id and extra_inputs:
            existing = dict(estado.values.get("technique_extra_inputs", {}))
            existing[tech_id] = extra_inputs
            update["technique_extra_inputs"] = existing
        if update:
            app.update_state(config, update)
        app.invoke(None, config)

    elif action in ("approve", "feedback"):
        estado  = app.get_state(config)
        update  = {
            "is_approved":   action == "approve",
            "user_feedback": feedback if action == "feedback" else "",
        }
        # If user edited the prompt, update it in state so redo picks it up
        if action == "feedback" and current_prompt is not None:
            idx  = estado.values.get("current_technique_index", 0)
            sel  = estado.values.get("selected_techniques", [])
            tech_id = sel[idx] if idx < len(sel) else None
            if tech_id:
                prompts = dict(estado.values.get("technique_prompts", {}))
                if current_prompt:
                    prompts[tech_id] = current_prompt
                else:
                    prompts.pop(tech_id, None)
                update["technique_prompts"] = prompts
        app.update_state(config, update)
        app.invoke(None, config)

    estado = app.get_state(config)
    values = estado.values
    next_nodes = estado.next

    siguiente = next_nodes[0] if next_nodes else "END"

    idx      = values.get("current_technique_index", 0)
    selected = values.get("selected_techniques", [])
    outputs  = values.get("technique_outputs", {})

    current_id = selected[idx] if idx < len(selected) else None
    output     = outputs.get(current_id) if current_id else None

    # True when pre_technique interrupted (no output yet for current technique)
    awaiting_pre_inputs = (
        siguiente == "run_technique"
        and current_id is not None
        and current_id not in outputs
    )

    return {
        "estado":             siguiente,
        "current_index":      idx,
        "technique_id":       current_id,
        "output":             output,
        "all_outputs":        outputs,
        "awaiting_pre_inputs": awaiting_pre_inputs,
    }
