from nodes.base import BaseNode
from utils.prompt_loader import load_prompt


class GenerateGMNode(BaseNode):

    def __init__(self, llm, prompt_path):
        super().__init__(llm)
        self.template = load_prompt(prompt_path)

    def __call__(self, state):
        prompt = self.template.format(
            MapSchema=state["map_schema"]
        )

        response = self.llm.invoke(prompt)

        return {**state, "raw_output": response.content}