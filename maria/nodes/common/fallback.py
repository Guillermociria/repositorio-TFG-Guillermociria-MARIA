class FallbackNode:

    def __call__(self, state):
        return {
            **state,
            "errors": "max_retries_exceeded"
        }