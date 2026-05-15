import sys
import os
import json
import time
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from nodes.ltg.subgraph_ltg import build_ltg_subgraph
from nodes.sq.subgraph_sq import build_sq_subgraph
from nodes.map.subgraph_map import build_map_subgraph
from nodes.generate_map.subgraph_generate_map import build_generate_map_subgraph
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from state.agent_state import MasterState
from utils.prompt_loader import load_prompt

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

# ──────────────────────────────────────────────────────────────────────────────
# LLM factory + caches
# ──────────────────────────────────────────────────────────────────────────────

_LLM_CACHE: dict = {}       # (provider, key_prefix) -> LLM instance
_SUBGRAPH_CACHE: dict = {}  # (builder_name, llm_id) -> compiled subgraph


def build_llm(provider: str = "google", api_key: str | None = None):
    """Return a cached LLM instance for the given provider and key."""
    key_prefix = (api_key or "")[:16]
    cache_key = (provider, key_prefix)
    if cache_key in _LLM_CACHE:
        return _LLM_CACHE[cache_key]

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        instance = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            model_kwargs={"response_format": {"type": "json_object"}},
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        instance = ChatAnthropic(
            model="claude-sonnet-4-6-20251001",
            temperature=0.7,
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
        )
    else:  # google (default)
        instance = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.7,
            convert_system_message_to_human=True,
            response_mime_type="application/json",
            google_api_key=api_key or os.getenv("GEMINI_API_KEY"),
        )
    _LLM_CACHE[cache_key] = instance
    return instance


def _get_subgraph(builder_fn, llm_instance):
    """Return a cached compiled subgraph for the given builder + LLM."""
    cache_key = (builder_fn.__name__, id(llm_instance))
    if cache_key not in _SUBGRAPH_CACHE:
        _SUBGRAPH_CACHE[cache_key] = builder_fn(llm_instance)
    return _SUBGRAPH_CACHE[cache_key]


# Default LLM (system Google key)
llm = build_llm("google")

# Pre-compiled subgraphs using default LLM
ltg_app          = _get_subgraph(build_ltg_subgraph, llm)
sq_app           = _get_subgraph(build_sq_subgraph, llm)
map_app          = _get_subgraph(build_map_subgraph, llm)
generate_map_app = _get_subgraph(build_generate_map_subgraph, llm)

# Resolve prompt paths relative to this file
_PROMPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prompts'))

def _prompt_path(filename):
    return os.path.join(_PROMPTS, filename)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _build_context_str(technique_outputs: dict) -> str:
    """Serialize all previous technique outputs into a readable context string."""
    if not technique_outputs:
        return "No previous technique outputs available."
    parts = []
    for tech_id, output in technique_outputs.items():
        parts.append(f"[{tech_id.upper()}]\n{json.dumps(output, ensure_ascii=False, indent=2)}")
    return "\n\n".join(parts)


_QUOTA_KEYWORDS = [
    '429', 'rate limit', 'quota', 'resource exhausted', 'resourceexhausted',
    'too many requests', 'exhausted', 'rate_limit_exceeded',
]
_AUTH_KEYWORDS = ['401', 'unauthorized', 'invalid api key', 'authentication', 'api key']


def _classify_llm_error(e: Exception) -> str:
    s = str(e).lower()
    if any(k in s for k in _QUOTA_KEYWORDS):
        return 'quota_exceeded'
    if any(k in s for k in _AUTH_KEYWORDS):
        return 'auth_error'
    return 'unknown_error'


def _invoke_with_retry(llm_instance, prompt, max_retries: int = 3):
    """Invoke LLM with exponential backoff on quota/rate-limit errors."""
    for attempt in range(max_retries):
        try:
            return llm_instance.invoke(prompt)
        except Exception as e:
            if _classify_llm_error(e) == 'quota_exceeded' and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"⏳ Quota/rate-limit (intento {attempt + 1}/{max_retries}), reintentando en {wait}s…")
                time.sleep(wait)
                continue
            raise


def _language_instruction(state: MasterState) -> str:
    lang = (state.get("language") or "español").strip()
    return f"\n\nIDIOMA: Escribe todo el contenido textual de la respuesta en {lang}. Mantén las claves JSON en inglés o español técnico."


def _run_generic_llm(state: MasterState, prompt_template: str, custom_prompt: str | None, extra_inputs: dict | None = None, llm_instance=None) -> dict:
    """Run a technique using a prompt template + generic LLM call."""
    _llm = llm_instance or llm
    template = custom_prompt if custom_prompt else prompt_template
    previous_ctx = _build_context_str(state.get("technique_outputs", {}))
    prompt = template.format(
        problem_definition=state.get("problem_definition", ""),
        target_user=state.get("target_user", ""),
        pain_points=state.get("pain_points", ""),
        initial_idea=state.get("initial_idea", ""),
        previous_context=previous_ctx,
    )
    if extra_inputs:
        prompt += "\n\nInstrucciones adicionales del usuario:\n" + json.dumps(extra_inputs, ensure_ascii=False, indent=2)
    feedback = state.get("user_feedback", "")
    if feedback:
        prompt += f"\n\nFeedback de revisión (mejora tu respuesta anterior basándote en esto):\n{feedback}"
    prompt += _language_instruction(state)
    response = _invoke_with_retry(_llm, prompt)
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {"raw": response.content}


# ──────────────────────────────────────────────────────────────────────────────
# Per-technique runner functions
# Each receives (state, custom_prompt) and returns a dict output.
# ──────────────────────────────────────────────────────────────────────────────

def _run_ltg(state: MasterState, custom_prompt: str | None, extra_inputs: dict | None = None, llm_instance=None) -> dict:
    problem = state.get("problem_definition", "")
    if extra_inputs and extra_inputs.get("focus"):
        problem += f"\n\nFoco adicional: {extra_inputs['focus']}"
    feedback = state.get("user_feedback", "")
    if feedback:
        problem += f"\n\nFeedback de revisión: {feedback}"
    inputs = {
        "problem_definition": problem,
        "target_user":        state.get("target_user", ""),
        "pain_points":        state.get("pain_points", ""),
        "initial_idea":       state.get("initial_idea", ""),
        "retries": 0, "validated": False,
    }
    if custom_prompt:
        inputs["_custom_prompt"] = custom_prompt
    inputs["_language_instruction"] = _language_instruction(state)
    app = _get_subgraph(build_ltg_subgraph, llm_instance or llm)
    result = app.invoke(inputs)
    return result.get("ltg_analysis", {})


def _run_sq(state: MasterState, custom_prompt: str | None, extra_inputs: dict | None = None, llm_instance=None) -> dict:
    prev = state.get("technique_outputs", {})
    preferred = prev.get("ltg", {}).get("alternatives", {}).get("user_centric", "")
    if extra_inputs and extra_inputs.get("goal_direction"):
        preferred = extra_inputs["goal_direction"]
    feedback = state.get("user_feedback", "")
    if feedback:
        preferred = (preferred + f"\n\nFeedback de revisión: {feedback}").strip()
    inputs = {
        "problem_definition":    state.get("problem_definition", ""),
        "ltg_analysis":          prev.get("ltg", {}),
        "prefered_goal":         preferred,
        "initial_idea":          state.get("initial_idea", ""),
        "retries": 0, "validated": False,
        "_language_instruction": _language_instruction(state),
    }
    app = _get_subgraph(build_sq_subgraph, llm_instance or llm)
    result = app.invoke(inputs)
    return result.get("final_sq", {})


def _run_map(state: MasterState, custom_prompt: str | None, extra_inputs: dict | None = None, llm_instance=None) -> dict:
    prev = state.get("technique_outputs", {})
    inputs = {
        "problem_definition": state.get("problem_definition", ""),
        "ltg_analysis":       prev.get("ltg", {}),
        "prefered_goal":      prev.get("ltg", {}).get("alternatives", {}).get("user_centric", ""),
        "initial_idea":       state.get("initial_idea", ""),
        "final_sq":           prev.get("sq", {}),
        "retries": 0, "validated": False,
    }
    app = _get_subgraph(build_map_subgraph, llm_instance or llm)
    result = app.invoke(inputs)
    return result.get("map_schema", {})


def _run_generate_map(state: MasterState, custom_prompt: str | None, extra_inputs: dict | None = None, llm_instance=None) -> dict:
    prev = state.get("technique_outputs", {})
    inputs = {
        "map_schema": prev.get("map", {}),
        "retries": 0, "validated": False,
    }
    app = _get_subgraph(build_generate_map_subgraph, llm_instance or llm)
    result = app.invoke(inputs)
    return {"map_code": result.get("map_code", "")}


def _run_mapa_empatia(state: MasterState, custom_prompt: str | None, extra_inputs: dict | None = None, llm_instance=None) -> dict:
    template = load_prompt(_prompt_path("promptMapaEmpatia.txt"))
    return _run_generic_llm(state, template, custom_prompt, extra_inputs, llm_instance)


def _run_entrevistas(state: MasterState, custom_prompt: str | None, extra_inputs: dict | None = None, llm_instance=None) -> dict:
    template = load_prompt(_prompt_path("promptEntrevistas.txt"))
    return _run_generic_llm(state, template, custom_prompt, extra_inputs, llm_instance)


def _run_hmw(state: MasterState, custom_prompt: str | None, extra_inputs: dict | None = None, llm_instance=None) -> dict:
    _llm = llm_instance or llm
    template = load_prompt(_prompt_path("promptHowMightWeReduced.txt"))
    prev = state.get("technique_outputs", {})
    previous_ctx = _build_context_str(prev)
    prompt = (custom_prompt or template).format(
        problem_definition=state.get("problem_definition", ""),
        target_user=state.get("target_user", ""),
        pain_points=state.get("pain_points", ""),
        initial_idea=state.get("initial_idea", ""),
        previous_context=previous_ctx,
    )
    if extra_inputs:
        prompt += "\n\nInstrucciones adicionales del usuario:\n" + json.dumps(extra_inputs, ensure_ascii=False, indent=2)
    feedback = state.get("user_feedback", "")
    if feedback:
        prompt += f"\n\nFeedback de revisión (mejora tu respuesta anterior basándote en esto):\n{feedback}"
    prompt += _language_instruction(state)
    response = _invoke_with_retry(_llm, prompt)
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {"raw": response.content}


def _run_pov(state: MasterState, custom_prompt: str | None, extra_inputs: dict | None = None, llm_instance=None) -> dict:
    template = load_prompt(_prompt_path("promptPOV.txt"))
    return _run_generic_llm(state, template, custom_prompt, extra_inputs, llm_instance)


def _run_brainstorming(state: MasterState, custom_prompt: str | None, extra_inputs: dict | None = None, llm_instance=None) -> dict:
    template = load_prompt(_prompt_path("promptBrainstorming.txt"))
    return _run_generic_llm(state, template, custom_prompt, extra_inputs, llm_instance)


def _run_prototipado(state: MasterState, custom_prompt: str | None, extra_inputs: dict | None = None, llm_instance=None) -> dict:
    template = load_prompt(_prompt_path("promptPrototipado.txt"))
    return _run_generic_llm(state, template, custom_prompt, extra_inputs, llm_instance)


def _run_testing(state: MasterState, custom_prompt: str | None, extra_inputs: dict | None = None, llm_instance=None) -> dict:
    template = load_prompt(_prompt_path("promptTesting.txt"))
    return _run_generic_llm(state, template, custom_prompt, extra_inputs, llm_instance)


def _run_customer_journey(state: MasterState, custom_prompt: str | None, extra_inputs: dict | None = None, llm_instance=None) -> dict:
    template = load_prompt(_prompt_path("promptCustomerJourney.txt"))
    return _run_generic_llm(state, template, custom_prompt, extra_inputs, llm_instance)


# ──────────────────────────────────────────────────────────────────────────────
# Registry: technique_id -> runner function
# ──────────────────────────────────────────────────────────────────────────────

TECHNIQUE_REGISTRY = {
    "ltg":              _run_ltg,
    "sq":               _run_sq,
    "map":              _run_map,
    "generate_map":     _run_generate_map,
    "mapa_empatia":     _run_mapa_empatia,
    "entrevistas":      _run_entrevistas,
    "hmw":              _run_hmw,
    "pov":              _run_pov,
    "brainstorming":    _run_brainstorming,
    "prototipado":      _run_prototipado,
    "testing":          _run_testing,
    "customer_journey": _run_customer_journey,
}


# ──────────────────────────────────────────────────────────────────────────────
# Master Graph Nodes
# ──────────────────────────────────────────────────────────────────────────────

def pre_technique(state: MasterState) -> dict:
    """Interrupt point before each technique — allows user to provide extra inputs."""
    return {}


def run_technique(state: MasterState) -> dict:
    idx        = state.get("current_technique_index", 0)
    techniques = state.get("selected_techniques", [])
    tech_id    = techniques[idx]
    prompts    = state.get("technique_prompts", {})
    custom     = prompts.get(tech_id)
    extra      = state.get("technique_extra_inputs", {}).get(tech_id)

    providers  = state.get("technique_llm_providers") or {}
    api_keys   = state.get("user_api_keys") or {}
    provider   = providers.get(tech_id, "google")
    api_key    = api_keys.get(provider) or None
    tech_llm   = build_llm(provider, api_key)

    runner = TECHNIQUE_REGISTRY.get(tech_id)

    def _run_with(llm_instance):
        if runner is not None:
            return runner(state, custom, extra, llm_instance)
        if custom:
            return _run_generic_llm(state, custom, None, extra, llm_instance)
        return None

    api_keys = state.get("user_api_keys") or {}
    fallback_providers = [p for p in ("openai", "anthropic", "google") if p != provider and api_keys.get(p)]
    fallback_providers.append("google")  # system key as last resort
    candidates = [(provider, api_key)] + [(p, api_keys.get(p)) for p in fallback_providers]
    seen = set()
    candidates = [(p, k) for p, k in candidates if not (p in seen or seen.add(p))]

    print(f"🚀 Ejecutando técnica [{idx + 1}/{len(techniques)}]: {tech_id} (LLM: {provider})")
    output = None
    last_error = None
    for attempt_provider, attempt_key in candidates:
        attempt_llm = build_llm(attempt_provider, attempt_key)
        try:
            result = _run_with(attempt_llm)
            if result is None:
                print(f"⚠️  Técnica desconocida y sin prompt: {tech_id}")
                output = {"error": f"Técnica '{tech_id}' no reconocida."}
            else:
                if attempt_provider != provider:
                    print(f"✅ Fallback exitoso a {attempt_provider} para técnica {tech_id}")
                output = result
            break
        except Exception as e:
            error_type = _classify_llm_error(e)
            print(f"❌ Error en técnica {tech_id} (LLM: {attempt_provider}, tipo: {error_type}): {e}")
            last_error = (attempt_provider, error_type, e)
            if error_type != 'quota_exceeded':
                break  # non-quota errors don't benefit from switching provider

    if output is None and last_error:
        attempt_provider, error_type, e = last_error
        user_msg = {
            'quota_exceeded': "Todos los proveedores LLM disponibles han agotado su cuota. Espera unos minutos e inténtalo de nuevo.",
            'auth_error':     f"Clave API de {attempt_provider} inválida o sin permisos. Revisa tu perfil.",
        }.get(error_type, f"Error inesperado con {attempt_provider}: {e}")
        output = {"llm_error": True, "provider": attempt_provider, "error_type": error_type, "message": user_msg}
    print(f"✅ Técnica completada: {tech_id}")

    outputs = dict(state.get("technique_outputs", {}))
    outputs[tech_id] = output
    return {"technique_outputs": outputs, "is_approved": False}


def advance_technique(state: MasterState) -> dict:
    """Increment the technique index and reset approval flag."""
    return {
        "current_technique_index": state.get("current_technique_index", 0) + 1,
        "is_approved": False,
        "user_feedback": "",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Routing
# ──────────────────────────────────────────────────────────────────────────────

def route_after_review(state: MasterState) -> str:
    """After interrupt: approved → advance, else retry."""
    if state.get("is_approved"):
        return "advance_technique"
    return "run_technique"


def route_after_advance(state: MasterState) -> str:
    """After advancing: more techniques → pre_technique questionnaire, else END."""
    idx        = state.get("current_technique_index", 0)
    techniques = state.get("selected_techniques", [])
    if idx < len(techniques):
        return "pre_technique"
    return END


# ──────────────────────────────────────────────────────────────────────────────
# Graph Assembly
# ──────────────────────────────────────────────────────────────────────────────

master_workflow = StateGraph(MasterState)
master_workflow.add_node("pre_technique",    pre_technique)
master_workflow.add_node("run_technique",    run_technique)
master_workflow.add_node("advance_technique", advance_technique)

master_workflow.set_entry_point("pre_technique")
master_workflow.add_edge("pre_technique", "run_technique")

master_workflow.add_conditional_edges(
    "run_technique",
    route_after_review,
    {"advance_technique": "advance_technique", "run_technique": "run_technique"},
)
master_workflow.add_conditional_edges(
    "advance_technique",
    route_after_advance,
    {"pre_technique": "pre_technique", END: END},
)


def get_compiled_master_graph(pool):
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()
    return master_workflow.compile(
        checkpointer=checkpointer,
        interrupt_after=["pre_technique", "run_technique"],
    )
