import sys
import os
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from nodes.ltg.subgraph_ltg import build_ltg_subgraph
from nodes.sq.subgraph_sq import build_sq_subgraph
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from state.agent_state import MasterState

# from subgraph_journey import build_journey_subgraph (Cuando lo tengas)
os.environ["GOOGLE_API_KEY"] = "AIzaSyAosE9Wi98BpEf5TVi7zGyOG5WLWx0hUGc"
# 1. Configuración del LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0.7,
    convert_system_message_to_human=True,
    response_mime_type="application/json"
)

DB_URI = "postgresql://usuario:password@localhost:5432/tu_db_django"

# El pool permite manejar múltiples peticiones concurrentes en la web
with ConnectionPool(conninfo=DB_URI, max_size=20) as pool:
    # 2. Instanciar el saver de Postgres
    checkpointer = PostgresSaver(pool)
    
    # 3. Solo la primera vez, crea las tablas necesarias en tu DB
    # checkpointer.setup() 

    # 4. Compilar el grafo con este checkpointer
    app = workflow.compile(checkpointer=checkpointer)
    
    # Ahora, cualquier hilo (thread_id) se guardará automáticamente en Postgres
    config = {"configurable": {"thread_id": "usuario_123"}}
    app.invoke(inputs, config)

# 2. Instanciamos los sub-grafos
ltg_app = build_ltg_subgraph(llm)
sq_app = build_sq_subgraph(llm)

# 3. Funciones puente (Wrappers)
def run_ltg_phase(state: MasterState):
    print("🚀 Jefe: Iniciando la fase LTG...")
    
    # Preparamos los datos para el sub-grafo
    inputs_para_ltg = {
        "problem_definition": state["problem_definition"],
        "target_user": state["target_user"],
        "pain_points": state["pain_points"],
        "initial_idea": state["initial_idea"],
        "retries": 0,
        "validated": False
    }
    
    resultado_subgrafo = ltg_app.invoke(inputs_para_ltg)
    
    print("✅ Jefe: Fase LTG completada.")
    return {"ltg_analysis": resultado_subgrafo.get("ltg_analysis")}

def run_sq_phase(state: MasterState):
    print("Iniciando fase SQ...")
    
    inputs_sq = {
        "problem_definition": state["problem_definition"],
        "ltg_result": state["ltg_analysis"],
        "prefered_goal": state["prefered_goal"],
        "initial_idea": state["initial_idea"],
        "retries": 0,
        "validated": False
    }
    
    resultado_sq = sq_app.invoke(inputs_sq)
    print("Fase SQ completada.")
    return {"sq_analysis": resultado_subgrafo.get("sq_analysis")}
    
# 4. Construimos el Grafo Maestro
master_workflow = StateGraph(MasterState)

master_workflow.add_node("phase_ltg", run_ltg_phase)
master_workflow.add_node("phase_sq", run_sq_phase)

master_workflow.set_entry_point("phase_ltg")
master_workflow.add_edge("phase_ltg", "phase_sq") # Luego cambiará a: "phase_ltg", "phase_journey"
master_workflow.add_edge("phase_sq", END)
master_app = master_workflow.compile()


if __name__ == "__main__":
    print("🏢 INICIANDO EL SISTEMA MAESTRO DEL DESIGN SPRINT 🏢\n")

    # 1. PREPARAMOS EL INPUT INICIAL
    # Esto simula los datos que un usuario escribiría en tu web de Django
    # Fíjate que las claves coinciden EXACTAMENTE con tu 'MasterState'
    input_usuario = {
        "problem_definition": "Los usuarios abandonan el carrito porque el proceso de pago tiene 5 pasos y es confuso.",
        "target_user": "Compradores online de entre 18 y 35 años que usan el móvil.",
        "pain_points": "Muchos formularios, carga lenta, desconfianza al poner la tarjeta.",
        "initial_idea": "Hacer un botón de 'Comprar en 1 clic' como el de Amazon.",
        
        # Opcional pero recomendado: Inicializar los resultados vacíos
        "ltg_analysis": None,
        "sq_analysis": None
    }

    # 2. INVOCAMOS AL GRAFO MAESTRO
    # ¡Le pasamos el diccionario directamente!
    print("Pulsado el botón 'Generar Sprint'...")
    estado_final_maestro = master_app.invoke(input_usuario)

    # 3. LEEMOS LOS RESULTADOS FINALES
    # Cuando esta línea se ejecute, el Jefe ya ha mandado trabajar al equipo LTG,
    # han hecho sus validaciones, sus reintentos, y han devuelto el resultado limpio.
    
    print("\n==================================================")
    print("🎉 RESULTADOS FINALES DEL SPRINT 🎉")
    print("==================================================\n")

    if estado_final_maestro.get("ltg_analysis"):
        print("✅ Long-Term Goal (LTG) Generado con éxito:")
        import json
        print(json.dumps(estado_final_maestro["ltg_analysis"], indent=2, ensure_ascii=False))
        print(json.dumps(estado_final_maestro["sq_analysis"], indent=2, ensure_ascii=False))
        # Aquí podrías poner tu código de guardar el JSON en la carpeta 'results'
        
    else:
        print("❌ El proceso terminó, pero no se pudo generar el LTG.")