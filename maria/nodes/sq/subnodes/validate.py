import json

class ValidateSQNode:

    def __call__(self, state):
        try:
            # 1. Intentamos cargar el JSON
            data = json.loads(state["raw_output"])
        except Exception as e:
            return {**state, "validated": False, "errors": f"invalid_json: {str(e)}"}

        # 2. Convertimos todas las claves del JSON a minúsculas para evitar errores
        # Esto nos protege si el LLM devuelve "Critique", "CRITIQUE" o "critique"
        data_lower_keys = {k.lower(): v for k, v in data.items()}

        required = ["pre_mortem_analysis", "skeptical_user_questions", "cynical_expert_questions", "fatal_flaw_assumption"]

        # 3. Validamos sobre el diccionario en minúsculas
        for key in required:
            if key not in data_lower_keys:
                return {
                    **state,
                    "validated": False,
                    "errors": f"missing_{key}"
                }

        # 4. Devolvemos el JSON validado (usamos el de minúsculas para mantener consistencia)
        return {
            **state,
            "validated": True,
            "sq_analysis": data_lower_keys
        }