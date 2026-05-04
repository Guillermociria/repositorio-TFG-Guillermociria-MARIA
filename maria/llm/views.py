# maria/llm/views.py
from django.shortcuts import render
from django.http import JsonResponse
from .services import ejecutar_agente_sprint  # Importamos el servicio que acabamos de crear

def sprint_view(request):
    # Aseguramos que el usuario tenga una sesión (thread_id)
    if not request.session.session_key:
        request.session.create()
    thread_id = request.session.session_key

    if request.method == "POST":
        feedback_usuario = request.POST.get('feedback')
        
        try:
            if feedback_usuario:
                # Continuar flujo con feedback
                resultado = ejecutar_agente_sprint(thread_id, feedback=feedback_usuario)
            else:
                # Iniciar flujo nuevo
                inputs = {
                    "problem_definition": request.POST.get('problema'),
                    "target_user": request.POST.get('usuario'),
                    "pain_points": request.POST.get('dolores'),
                    "initial_idea": request.POST.get('idea'),
                }
                resultado = ejecutar_agente_sprint(thread_id, inputs=inputs)

            return JsonResponse({
                "status": "success",
                "data": resultado
            })
            
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    # Si es GET, mostramos el formulario HTML
    return render(request, "agente_formulario.html")