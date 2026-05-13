import os
from django.core.management.base import BaseCommand
from llm.models import Technique

PROMPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'prompts')
)

def _read(filename):
    path = os.path.join(PROMPTS_DIR, filename)
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return f.read()
    return ''


BUILTIN_TECHNIQUES = [
    {
        'tech_id': 'ltg',
        'name': 'Long Term Goal',
        'icon': '🎯',
        'stage': 'definir',
        'inputs_description': 'Problema, usuario, dolores',
        'outputs_description': 'Objetivo LTG con alternativas y riesgos',
        'prompt_file': 'promptLongTermGoal.txt',
        'questionnaire': [
            {'id': 'focus', 'label': '¿Aspecto del problema en el que enfocarse?',
             'type': 'textarea', 'placeholder': 'Ej: Enfócate en la fase de adquisición de usuarios...'},
        ],
    },
    {
        'tech_id': 'sq',
        'name': 'Sprint Questions',
        'icon': '❓',
        'stage': 'definir',
        'inputs_description': 'LTG, problema',
        'outputs_description': 'Lista de sprint questions (riesgos a validar)',
        'prompt_file': 'promptSprintQuestions.txt',
        'questionnaire': [
            {'id': 'goal_direction', 'label': '¿Qué dirección de objetivo te interesa?',
             'type': 'textarea', 'placeholder': 'Ej: Prefiero un enfoque conservador orientado a retención...'},
        ],
    },
    {
        'tech_id': 'mapa_empatia',
        'name': 'Mapa de empatía',
        'icon': '🧠',
        'stage': 'empatizar',
        'inputs_description': 'Problema, usuario',
        'outputs_description': 'Mapa: piensa, siente, ve, escucha, dice, hace',
        'prompt_file': 'promptMapaEmpatia.txt',
        'questionnaire': [
            {'id': 'user_segment', 'label': '¿Segmento de usuario a explorar?',
             'type': 'text', 'placeholder': 'Ej: Usuarios primerizos, usuarios avanzados...'},
        ],
    },
    {
        'tech_id': 'entrevistas',
        'name': 'Entrevistas en profundidad',
        'icon': '🎤',
        'stage': 'empatizar',
        'inputs_description': 'Problema, usuario',
        'outputs_description': 'Guía con preguntas clave estructuradas',
        'prompt_file': 'promptEntrevistas.txt',
        'questionnaire': [
            {'id': 'n_interviews', 'label': 'Número de entrevistas a diseñar',
             'type': 'number', 'placeholder': '5'},
            {'id': 'format', 'label': 'Formato', 'type': 'select',
             'options': ['Presencial', 'Remoto', 'Híbrido']},
        ],
    },
    {
        'tech_id': 'hmw',
        'name': '¿Cómo podríamos...?',
        'icon': '💡',
        'stage': 'definir',
        'inputs_description': 'LTG, sprint questions',
        'outputs_description': 'Lista de oportunidades HMW',
        'prompt_file': 'promptHowMightWeReduced.txt',
        'questionnaire': [
            {'id': 'focus_area', 'label': '¿En qué área generar preguntas HMW?',
             'type': 'textarea', 'placeholder': 'Ej: Centra las preguntas en la fase de descubrimiento...'},
        ],
    },
    {
        'tech_id': 'pov',
        'name': 'POV',
        'icon': '👤',
        'stage': 'definir',
        'inputs_description': 'Usuario, mapa de empatía',
        'outputs_description': 'Declaración POV estructurada',
        'prompt_file': 'promptPOV.txt',
        'questionnaire': [
            {'id': 'user_archetype', 'label': '¿Arquetipo de usuario a explorar?',
             'type': 'text', 'placeholder': 'Ej: Millennial con poco tiempo, empresario autónomo...'},
        ],
    },
    {
        'tech_id': 'brainstorming',
        'name': 'Brainstorming',
        'icon': '⚡',
        'stage': 'idear',
        'inputs_description': 'HMW, POV',
        'outputs_description': 'Ideas ordenadas por viabilidad e impacto',
        'prompt_file': 'promptBrainstorming.txt',
        'questionnaire': [
            {'id': 'n_ideas', 'label': 'Ideas por categoría', 'type': 'number', 'placeholder': '5'},
            {'id': 'constraints', 'label': 'Restricciones o criterios',
             'type': 'textarea', 'placeholder': 'Ej: Solo soluciones digitales, presupuesto bajo...'},
        ],
    },
    {
        'tech_id': 'prototipado',
        'name': 'Prototipado rápido',
        'icon': '🛠️',
        'stage': 'prototipar',
        'inputs_description': 'Ideas seleccionadas',
        'outputs_description': 'Especificación del prototipo rápido',
        'prompt_file': 'promptPrototipado.txt',
        'questionnaire': [
            {'id': 'fidelity', 'label': 'Nivel de fidelidad', 'type': 'select',
             'options': ['Baja (sketches)', 'Media (wireframes)', 'Alta (mockup interactivo)']},
            {'id': 'platform', 'label': 'Plataforma', 'type': 'select',
             'options': ['Web', 'Móvil', 'Ambas', 'Otro']},
        ],
    },
    {
        'tech_id': 'testing',
        'name': 'Testing con usuarios',
        'icon': '🧪',
        'stage': 'testear',
        'inputs_description': 'Prototipo',
        'outputs_description': 'Plan de testing y criterios de éxito',
        'prompt_file': 'promptTesting.txt',
        'questionnaire': [
            {'id': 'n_participants', 'label': 'Número de participantes', 'type': 'number', 'placeholder': '5'},
            {'id': 'timeline', 'label': 'Plazo para el testing', 'type': 'text', 'placeholder': 'Ej: 1 semana'},
        ],
    },
    {
        'tech_id': 'customer_journey',
        'name': 'Customer Journey Map',
        'icon': '🗺️',
        'stage': 'empatizar',
        'inputs_description': 'Problema, usuario',
        'outputs_description': 'Journey map con etapas, emociones y touchpoints',
        'prompt_file': 'promptCustomerJourney.txt',
        'questionnaire': [
            {'id': 'focus_touchpoints', 'label': '¿Puntos de contacto a priorizar?',
             'type': 'textarea', 'placeholder': 'Ej: Prioriza la fase de resolución de problemas...'},
        ],
    },
]


class Command(BaseCommand):
    help = 'Carga las técnicas built-in en la base de datos'

    def handle(self, *args, **kwargs):
        created = updated = 0
        for t in BUILTIN_TECHNIQUES:
            prompt = _read(t['prompt_file'])
            obj, new = Technique.objects.update_or_create(
                tech_id=t['tech_id'],
                defaults={
                    'name':                t['name'],
                    'icon':                t['icon'],
                    'stage':               t['stage'],
                    'is_builtin':          True,
                    'inputs_description':  t['inputs_description'],
                    'outputs_description': t['outputs_description'],
                    'default_prompt':      prompt,
                    'questionnaire':       t.get('questionnaire', []),
                },
            )
            if new:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Técnicas: {created} creadas, {updated} actualizadas.'
        ))
