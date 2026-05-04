class ValidateMermaidNode:
    def __call__(self, state):
        raw_output = state.get("raw_output", "").strip()
        
        if not raw_output:
            return {
                **state, 
                "validated": False, 
                "errors": "empty_output: El modelo no ha devuelto ningún texto."
            }

        if "```" in raw_output:
            return {
                **state, 
                "validated": False, 
                "errors": "markdown_wrappers_detected: El código incluye ```, lo cual está prohibido. Debe ser texto plano."
            }

        if not raw_output.startswith("graph LR"):
            return {
                **state, 
                "validated": False, 
                "errors": "invalid_start: El código no empieza con 'graph LR'. Asegúrate de que el primer carácter sea la 'g'."
            }

        has_connection = "-->" in raw_output or "---" in raw_output
        has_subgraph = "subgraph " in raw_output
        
        if not (has_connection or has_subgraph):
            return {
                **state,
                "validated": False,
                "errors": "missing_structure: El código parece estar incompleto. No se detectaron conexiones (-->) ni subgrafos."
            }

        count_subgraph = raw_output.count("subgraph ")
        count_end = raw_output.count("end")
        
        if count_subgraph != count_end:
            return {
                **state,
                "validated": False,
                "errors": f"unmatched_subgraphs: Se encontraron {count_subgraph} 'subgraph' pero {count_end} 'end'. La sintaxis está rota."
            }

        return {
            **state,
            "validated": True,
            "mermaid_code": raw_output,
            "errors": None
        }