import sys
import os
import json
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from nodes.ltg.subgraph_ltg import build_ltg_subgraph
from nodes.sq.subgraph_sq import build_sq_subgraph
from nodes.map.subgraph_map import build_map_subgraph
from nodes.generate_map.subgraph_generate_map import build_generate_map_subgraph
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from state.agent_state import MasterState

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0.7,
    convert_system_message_to_human=True,
    response_mime_type="application/json"
)


ltg_app = build_ltg_subgraph(llm)
sq_app = build_sq_subgraph(llm)
map_app = build_map_subgraph(llm)
generate_map_app = build_generate_map_subgraph(llm)

def run_ltg_phase(state: MasterState):
    print("🚀 Jefe: Iniciando la fase LTG...")
    inputs_para_ltg = {
        "problem_definition": state.get("problem_definition", ""),
        "target_user": state.get("target_user", ""),
        "pain_points": state.get("pain_points", ""),
        "initial_idea": state.get("initial_idea", ""),
        "retries": 0,
        "validated": False
    }
    for e,i in inputs_para_ltg.items():
        print(f"{e}: {i}")
    resultado_ltg = ltg_app.invoke(inputs_para_ltg)
    print("✅ Jefe: Fase LTG completada.")
    return {"ltg_analysis": resultado_ltg.get("ltg_analysis")}

def run_sq_phase(state: MasterState):
    print("🚀 Jefe: Iniciando fase SQ...")
    inputs_sq = {
        "problem_definition": state.get("problem_definition", ""),
        "ltg_analysis": state.get("ltg_analysis", {}),
        "prefered_goal": state.get("prefered_goal", ""),
        "initial_idea": state.get("initial_idea", ""),
        "retries": 0,
        "validated": False
    }
    resultado_sq = sq_app.invoke(inputs_sq)
    print("✅ Jefe: Fase SQ completada.")
    return {"final_sq": resultado_sq.get("final_sq")}

def run_map_phase(state: MasterState):
    print("🚀 Jefe: Iniciando fase M...")
    inputs_map = {
        "problem_definition": state.get("problem_definition", ""),
        "ltg_analysis": state.get("ltg_analysis", {}),
        "prefered_goal": state.get("prefered_goal", ""),
        "initial_idea": state.get("initial_idea", ""),
        "final_sq": state.get("final_sq", {}),
        "retries": 0,
        "validated": False
    }
    resultado_map = map_app.invoke(inputs_map)
    print("✅ Jefe: Fase M completada.")
    return {"map_schema": resultado_map.get("map_schema")}

def run_generate_map_phase(state: MasterState):
    print("Generando mapa")
    inputs_generate_map={
        "map_schema": state.get("map_schema",{}),
        "retries": 0,
        "validated": False
    }
    resultado_generate_map = generate_map_app.invoke(inputs_generate_map)
    print("Mapa generado")
    return {"map_code": resultado_generate_map.get("map_code")}

def route_ltg(state: MasterState):
    if(state.get("is_approved")):
        return "phase_sq"
    return "phase_ltg"

def route_sq(state: MasterState):
    if(state.get("is_approved")):
        return "phase_map"
    return "phase_sq"

def route_map(state: MasterState):
    if(state.get("is_approved")):
        return "phase_generate_map"
    return "phase_map"

master_workflow = StateGraph(MasterState)
master_workflow.add_node("phase_ltg", run_ltg_phase)
master_workflow.add_node("phase_sq", run_sq_phase)
master_workflow.add_node("phase_map", run_map_phase)
master_workflow.add_node("phase_generate_map", run_generate_map_phase)

master_workflow.set_entry_point("phase_ltg")
master_workflow.add_edge("phase_ltg", "phase_sq")
master_workflow.add_edge("phase_sq", "phase_map")  
master_workflow.add_edge("phase_map", "phase_generate_map") 
master_workflow.add_edge("phase_generate_map", END)


def get_compiled_master_graph(pool):
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()
    return master_workflow.compile(checkpointer=checkpointer)


# BLOQUE DE PRUEBAS LOCALES
if __name__ == "__main__":
    print("🏢 INICIANDO EL SISTEMA MAESTRO DEL DESIGN SPRINT 🏢\n")

    DB_URI = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

    with ConnectionPool(conninfo=DB_URI, max_size=20) as pool:
        

        master_app = get_compiled_master_graph(pool)


        input_usuario = {
            "problem_definition": "Los usuarios abandonan el carrito porque el proceso de pago tiene 5 pasos y es confuso.",
            "target_user": "Compradores online de entre 18 y 35 años que usan el móvil.",
            "pain_points": "Muchos formularios, carga lenta, desconfianza al poner la tarjeta.",
            "initial_idea": "Hacer un botón de 'Comprar en 1 clic' como el de Amazon.",
        }

        config = {"configurable": {"thread_id": "sesion_prueba_001"}}


        print("Pulsado el botón 'Generar Sprint'...")
        estado_final_maestro = master_app.invoke(input_usuario, config)

        print("\n==================================================")
        print(" RESULTADOS FINALES DEL SPRINT ")
        print("==================================================\n")

        if estado_final_maestro.get("ltg_analysis"):
            print("✅ Long-Term Goal (LTG):")
            print(json.dumps(estado_final_maestro["ltg_analysis"], indent=2, ensure_ascii=False))

        if estado_final_maestro.get("final_sq"):
            print("\n✅ Sprint Questions (SQ):")
            print(json.dumps(estado_final_maestro["final_sq"], indent=2, ensure_ascii=False))
            
        if estado_final_maestro.get("map_schema"):
            print("\n✅ Map (Map):")
            print(json.dumps(estado_final_maestro["map_schema"], indent=2, ensure_ascii=False))
        
        if estado_final_maestro.get("map_code"):
            print("\n✅ Map Code (Map Code):")
            print(estado_final_maestro["map_code"])