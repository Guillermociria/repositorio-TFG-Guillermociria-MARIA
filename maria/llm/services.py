# maria/llm/services.py
import os
from psycopg_pool import ConnectionPool

# Importamos la lógica de tu grafo desde la carpeta nodes
from nodes.llm import get_compiled_master_graph

# Configuramos el pool globalmente para que Django lo reutilice
DB_URI = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
pool = ConnectionPool(conninfo=DB_URI, max_size=20, kwargs={"autocommit": True})

def ejecutar_agente_sprint(thread_id, inputs=None, feedback=None):
    """
    Función puente que la vista de Django llamará.
    """
    # Usamos tu función de nodes.llm
    app = get_compiled_master_graph(pool)
    
    config = {"configurable": {"thread_id": thread_id}}

    if feedback:
        # Si hay feedback, actualizamos el estado y reanudamos
        app.update_state(config, {"user_feedback": feedback}, as_node="phase_ltg") # Cambia "phase_ltg" por el nodo donde esperas la pausa
        return app.invoke(None, config)
    
    # Si no hay feedback, iniciamos desde el principio con los inputs
    return app.invoke(inputs, config)