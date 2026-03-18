class ValidationRouter:

    def __call__(self, state):
        if state["validated"]:
            return "next"

        if state["retries"] >= state["max_retries"]:
            return "fallback"

        return "fix"