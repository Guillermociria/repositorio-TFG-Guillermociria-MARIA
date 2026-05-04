import time
from nodes.base import BaseNode

class FixMNode(BaseNode):

    def __call__(self, state):
        print("Pausando 3 segundos para no saturar la API...")
        time.sleep(3)
        prompt = f"""
        El output es inválido.

        ERROR: {state['errors']}

        OUTPUT:
        {state['raw_output']}

        Corrige y devuelve JSON válido.
        """

        response = self.llm.invoke(prompt)

        return {
            **state,
            "raw_output": response.content,
            "retries": state["retries"] + 1
        }