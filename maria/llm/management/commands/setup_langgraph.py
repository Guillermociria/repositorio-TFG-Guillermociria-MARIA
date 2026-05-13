from django.core.management.base import BaseCommand
from llm.services import get_pool
from langgraph.checkpoint.postgres import PostgresSaver

class Command(BaseCommand):
    help = 'Crea las tablas necesarias en Postgres para LangGraph'

    def handle(self, *args, **kwargs):
        self.stdout.write("Configurando tablas de LangGraph...")
        pool = get_pool()
        try:
            saver = PostgresSaver(pool)
            saver.setup()
            self.stdout.write(self.style.SUCCESS('¡Tablas de LangGraph creadas/verificadas con éxito!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al crear las tablas: {e}'))
        finally:
            pool.close()