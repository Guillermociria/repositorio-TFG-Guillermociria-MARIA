import json

class ValidateLTGNode:

    def __call__(self, state):
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