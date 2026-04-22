def load_prompt(path: str) -> str:
    with open(path, "r") as f:
        return f.read()