import json

class ValidateLTGNode:

    def __call__(self, state):
        try:
            data = json.loads(state["raw_output"])
        except Exception as e:
            return {**state, "validated": False, "errors": f"invalid_json: {str(e)}"}
        data_lower_keys = {k.lower(): v for k, v in data.items()}
        required = ["critique", "assumptions", "alternatives", "risks"]
        for key in required:
            if key not in data_lower_keys:
                return {
                    **state,
                    "validated": False,
                    "errors": f"missing_{key}"
                }
        return {
            **state,
            "validated": True,
            "ltg_analysis": data_lower_keys
        }
        