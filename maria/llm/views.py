# maria/llm/views.py
import json
import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from .services import ejecutar_agente_sprint, get_session_state
from .models import Technique, SprintSession


# ── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if name:
            stages = request.POST.getlist('stages')
            session = SprintSession.objects.create(
                user=request.user,
                name=name,
                description=description,
                stages=stages,
            )
            return redirect('sprint_session', session_id=session.pk)
    sessions = SprintSession.objects.filter(user=request.user)
    return render(request, 'dashboard.html', {'sessions': sessions})


# ── Sprint ──────────────────────────────────────────────────────────────────

@login_required
def sprint_view(request, session_id):
    session = get_object_or_404(SprintSession, pk=session_id, user=request.user)
    thread_id = str(session.thread_id)

    if request.method == "POST":
        action = request.POST.get("action")

        try:
            if action == "start":
                selected_raw   = request.POST.get("selected_techniques", "[]")
                prompts_raw    = request.POST.get("technique_prompts", "{}")
                providers_raw  = request.POST.get("technique_llm_providers", "{}")

                user = request.user
                user_api_keys = {}
                if getattr(user, "google_api_key", None):
                    user_api_keys["google"] = user.google_api_key
                if getattr(user, "openai_api_key", None):
                    user_api_keys["openai"] = user.openai_api_key
                if getattr(user, "anthropic_api_key", None):
                    user_api_keys["anthropic"] = user.anthropic_api_key

                inputs = {
                    "problem_definition":      request.POST.get("problema", ""),
                    "target_user":             request.POST.get("usuario", ""),
                    "pain_points":             request.POST.get("dolores", ""),
                    "initial_idea":            request.POST.get("idea", ""),
                    "selected_techniques":     json.loads(selected_raw),
                    "technique_prompts":       json.loads(prompts_raw),
                    "technique_llm_providers": json.loads(providers_raw),
                    "user_api_keys":           user_api_keys,
                    "current_technique_index": 0,
                    "technique_outputs":       {},
                    "technique_extra_inputs":  {},
                    "is_approved":             False,
                    "user_feedback":           "",
                }
                resultado = ejecutar_agente_sprint(thread_id, inputs=inputs, action=action)

            elif action == "pre_inputs":
                extra_raw = request.POST.get("extra_inputs", "{}")
                resultado = ejecutar_agente_sprint(
                    thread_id,
                    action=action,
                    extra_inputs=json.loads(extra_raw),
                )

            else:
                feedback       = request.POST.get("feedback", "")
                current_prompt = request.POST.get("current_prompt", None)
                resultado = ejecutar_agente_sprint(
                    thread_id,
                    feedback=feedback,
                    action=action,
                    current_prompt=current_prompt,
                )

            if resultado.get('estado') in ('END', '__end__', None, ''):
                session.status = 'completed'
                session.save()

            return JsonResponse({"status": "success", "data": resultado})

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    all_techniques = list(
        Technique.objects.values('tech_id', 'name', 'icon', 'stage', 'is_builtin', 'inputs_description', 'outputs_description', 'questionnaire')
    )
    existing_state = get_session_state(str(session.thread_id))

    user = request.user
    available_providers = [{"id": "google", "label": "Gemini 2.5 Flash"}]
    if getattr(user, "openai_api_key", None):
        available_providers.append({"id": "openai", "label": "GPT-4o"})
    if getattr(user, "anthropic_api_key", None):
        available_providers.append({"id": "anthropic", "label": "Claude Sonnet"})

    return render(request, "agente_formulario.html", {
        "all_techniques":      all_techniques,
        "session":             session,
        "session_stages":      json.dumps(session.stages or []),
        "existing_state":      json.dumps(existing_state) if existing_state else "null",
        "available_providers": json.dumps(available_providers),
        "is_admin":            request.user.is_staff,
    })


# ── Technique Catalog page ───────────────────────────────────────────────────

@login_required
def catalog_view(request):
    techniques = list(
        Technique.objects.values(
            'tech_id', 'name', 'icon', 'stage', 'is_builtin',
            'inputs_description', 'outputs_description',
        ).order_by('stage', 'name')
    )
    return render(request, 'catalog.html', {'techniques': techniques})


# ── Technique CRUD ───────────────────────────────────────────────────────────

def technique_list(request):
    techs = list(
        Technique.objects.values('tech_id', 'name', 'icon', 'stage', 'inputs_description', 'outputs_description')
    )
    return JsonResponse({"techniques": techs})


@login_required
@require_POST
def technique_create(request):
    if not request.user.is_staff:
        return JsonResponse({"error": "Solo los administradores pueden crear técnicas."}, status=403)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    tech_id = data.get("tech_id", "").strip()
    name    = data.get("name", "").strip()
    prompt  = data.get("default_prompt", "").strip()

    if not tech_id or not name or not prompt:
        return JsonResponse({"error": "tech_id, name y default_prompt son obligatorios"}, status=400)

    if Technique.objects.filter(tech_id=tech_id).exists():
        return JsonResponse({"error": f"Ya existe una técnica con ID '{tech_id}'"}, status=400)

    questionnaire = data.get("questionnaire", [])
    if not isinstance(questionnaire, list):
        questionnaire = []

    tech = Technique.objects.create(
        tech_id             = tech_id,
        name                = name,
        icon                = data.get("icon", "⚙️") or "⚙️",
        stage               = data.get("stage", "") or "",
        inputs_description  = data.get("inputs_description", ""),
        outputs_description = data.get("outputs_description", ""),
        default_prompt      = prompt,
        questionnaire       = questionnaire,
    )
    return JsonResponse({"ok": True, "tech_id": tech.tech_id})


@login_required
@require_http_methods(["DELETE"])
def technique_delete(request, tech_id):
    if not request.user.is_staff:
        return JsonResponse({"error": "Solo los administradores pueden eliminar técnicas."}, status=403)
    deleted, _ = Technique.objects.filter(tech_id=tech_id).delete()
    if deleted:
        return JsonResponse({"ok": True})
    return JsonResponse({"error": "No encontrada"}, status=404)


# ── Technique Simulate ───────────────────────────────────────────────────────

@login_required
@require_POST
def technique_simulate(request, tech_id):
    """Simulate realistic user responses to a technique's output (e.g. answer interview questions)."""
    tech = get_object_or_404(Technique, tech_id=tech_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    technique_output = data.get("output", {})
    target_user = data.get("target_user", "el usuario objetivo")
    problem_definition = data.get("problem_definition", "")

    try:
        from nodes.llm import build_llm
        llm_instance = build_llm("google")
        output_str = json.dumps(technique_output, ensure_ascii=False, indent=2)
        prompt = (
            f"Eres un facilitador experto en Design Sprint que simula respuestas realistas.\n\n"
            f"La técnica '{tech.name}' ha generado el siguiente resultado:\n{output_str}\n\n"
            f"Contexto del proyecto:\n"
            f"- Problema: {problem_definition}\n"
            f"- Usuario objetivo: {target_user}\n\n"
            f"Simula cómo respondería '{target_user}' a este contenido. "
            f"Si hay preguntas, genera respuestas realistas como si fueras ese usuario. "
            f"Si hay tareas o escenarios de test, simula su comportamiento y reacciones. "
            f"Sé específico y realista.\n\n"
            f"OUTPUT FORMAT: Devuelve SOLO JSON válido. Sin markdown. "
            f"Usa claves descriptivas para cada respuesta simulada."
        )
        response = llm_instance.invoke(prompt)
        try:
            result = json.loads(response.content)
        except (json.JSONDecodeError, ValueError):
            result = {"respuestas_simuladas": response.content}
        return JsonResponse({"ok": True, "output": result})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── Export ───────────────────────────────────────────────────────────────────

@login_required
def export_session(request, session_id):
    session = get_object_or_404(SprintSession, pk=session_id, user=request.user)
    state   = get_session_state(str(session.thread_id))

    export = {
        "session": {
            "id":          session.pk,
            "name":        session.name,
            "description": session.description,
            "status":      session.status,
            "stages":      session.stages,
            "created_at":  session.created_at.isoformat(),
        },
        "inputs": {},
        "selected_techniques": [],
        "technique_outputs":   {},
        "exported_at": datetime.datetime.utcnow().isoformat() + "Z",
    }

    if state:
        export["inputs"] = {
            "problem_definition": state.get("problem_definition", ""),
            "target_user":        state.get("target_user", ""),
            "pain_points":        state.get("pain_points", ""),
            "initial_idea":       state.get("initial_idea", ""),
        }
        export["selected_techniques"] = state.get("selected_techniques", [])
        export["technique_outputs"]   = state.get("all_outputs", {})

    filename = f"sprint_{session.pk}_{session.name[:30].replace(' ', '_')}.json"
    response = HttpResponse(
        json.dumps(export, ensure_ascii=False, indent=2),
        content_type="application/json",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ── Delete session ────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["DELETE"])
def delete_session(request, session_id):
    session = get_object_or_404(SprintSession, pk=session_id, user=request.user)
    session.delete()
    return JsonResponse({"ok": True})
