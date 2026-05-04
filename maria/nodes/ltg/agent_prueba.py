import sys
import os
import json
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()
ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(ruta_raiz)

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI

from state_prueba import AgentState
from subnodes.generate import GenerateLTGNode
from subnodes.validate import ValidateLTGNode
from subnodes.fix import FixLTGNode


# Configura tu API Key
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

memory = MemorySaver()

# Inicializamos el modelo
# Tip: 'json_mode' ayuda a que el modelo se esfuerce en devolver JSON válido
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0.7,
    convert_system_message_to_human=True,
    response_mime_type="application/json"
)

ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
ruta_prompt = os.path.join(ruta_raiz, "prompts", "promptLongTermGoal.txt")


generate_node = GenerateLTGNode(llm, ruta_prompt)
validate_node = ValidateLTGNode()
fix_node = FixLTGNode(llm)

# 2. Crear el Grafo
workflow = StateGraph(AgentState)

# Añadir Nodos
workflow.add_node("generate", generate_node)
workflow.add_node("validate", validate_node)
workflow.add_node("fix", fix_node)

# Definir Aristas (Edges)
workflow.set_entry_point("generate")
workflow.add_edge("generate", "validate")

# Aristas Condicionales: Si no es válido y hay pocos reintentos, ir a 'fix'
def should_continue(state):
    if state["validated"]:
        return END
    if state["retries"] >= 3: # Límite de seguridad
        return END
    return "fix"

workflow.add_conditional_edges(
    "validate", 
    should_continue,
    {
        END: END,
        "fix": "fix"
    }
)
workflow.add_edge("fix", "validate")

# Compilar
app = workflow.compile()


input_data = {
    "problem_definition": 
        """
        Los usuarios se frustran porque la app de reservas es muy lenta al cargar los horarios.
        """,
    "target_user": 
        """
        Profesionales ocupados de entre 25 y 45 años."""
        ,
    "pain_points": 
        """
        Tiempos de espera largos, interfaz confusa, pérdida de tiempo.
        """,
    "initial_idea": 
        """
        Tenemos un modelo vista controlador con base de datos Mongo y el resto escrito en django,
        está usando react para el frontend y queremos desplegar en una máquina de digital ocean.
        """,
    "retries": 0,         # Inicializamos el contador de reintentos
    "validated": False    # Estado inicial
}

# 2. Ejecutar el grafo pasándole los datos
print("Ejecutando el agente de LangGraph...\n")

print("\n--- Estructura del Grafo ---")
app.get_graph().print_ascii()
print("----------------------------\n")

final_state = app.invoke(input_data)


# 3. Mostrar los resultados
if final_state.get("validated"):
    print("¡ÉXITO! Análisis del Long-Term Goal generado y validado:")
    print("--------------------------------------------------")
    # Imprimimos el JSON ya parseado que guardó ValidateLTGNode
    
    print(json.dumps(final_state.get("ltg_analysis"), indent=2, ensure_ascii=False))
    resultado_final = final_state.get("ltg_analysis")
    os.makedirs("results", exist_ok=True)
        
    # B. Generar un nombre de archivo único con la fecha y hora actual
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"ltg_result_{timestamp}.json"
    ruta_archivo = os.path.join("results", nombre_archivo)
    
    # C. Escribir el archivo
    # Importante: usar encoding='utf-8' y ensure_ascii=False para guardar bien los acentos
    with open(ruta_archivo, "w", encoding="utf-8") as archivo:
        json.dump(resultado_final, archivo, indent=2, ensure_ascii=False)
        
    print(f"\n ¡JSON guardado exitosamente en: {ruta_archivo}")
else:
    print("ERROR: El agente no logró generar un JSON válido tras los reintentos.")
    print(f"Motivo del error: {final_state.get('errors')}")
    print("\nOutput crudo del modelo:")
    print(final_state.get("raw_output"))