class BaseNode:
    def __init__(self, llm):
        self.llm = llm

    def __call__(self, state):
        raise NotImplementedError