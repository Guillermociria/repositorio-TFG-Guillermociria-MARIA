from nodes.base import BaseNode
from utils.prompt_loader import load_prompt


class GenerateMNode(BaseNode):

    def __init__(self, llm, prompt_path):
        super().__init__(llm)
        self.template = load_prompt(prompt_path)

    def __call__(self, state):
        prompt = self.template.format(
            ProblemDefinition=state["problem_definition"],
            LTGResult=state["ltg_analysis"],
            PreferedGoal=state["prefered_goal"],
            InitialIdea=state["initial_idea"],
            SQResult=state["final_sq"]
        )

        response = self.llm.invoke(prompt)

        return {**state, "raw_output": response.content}