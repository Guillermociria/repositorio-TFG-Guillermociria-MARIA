"""
Pruebas de integración — flujo completo Django + DB.
El servicio LangGraph sigue mockeado (requiere infraestructura externa),
pero el resto del stack (vistas, modelos, ORM, autenticación) es real.
"""
import json
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from user.models import User
from llm.models import SprintSession, Technique


_END_STATE = {
    "estado": "END",
    "current_index": 1,
    "technique_id": None,
    "output": None,
    "all_outputs": {"ltg": {"critique": "done", "assumptions": [], "alternatives": [], "risks": []}},
    "awaiting_pre_inputs": False,
}

_REVIEW_STATE = {
    "estado": "review",
    "current_index": 0,
    "technique_id": "ltg",
    "output": {"critique": "analysis", "assumptions": ["a"], "alternatives": ["b"], "risks": ["c"]},
    "all_outputs": {},
    "awaiting_pre_inputs": False,
}


# ── Ciclo de vida completo de una sesión ──────────────────────────────────────

class TestSprintSessionLifecycle(TestCase):
    """
    Verifica que los pasos reales de un sprint se encadenan correctamente:
    crear sesión → abrir sprint → iniciar → aprobar → sesión completada.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='user_integ',
            email='integ@test.com',
            password='ValidPass123!',
        )
        self.client.force_login(self.user)
        Technique.objects.create(
            tech_id='ltg',
            name='Learn the Goal',
            stage='empatizar',
            is_builtin=True,
            default_prompt='Analyze the problem.',
        )

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_REVIEW_STATE)
    def test_create_session_then_start_sprint(self, mock_exec, mock_state):
        # Paso 1: crear sesión desde el dashboard
        response = self.client.post(reverse('dashboard'), {
            'name': 'Sprint Integración',
            'description': 'Prueba end-to-end',
            'stages': ['empatizar'],
        })
        self.assertEqual(response.status_code, 302)
        session = SprintSession.objects.get(user=self.user, name='Sprint Integración')
        self.assertEqual(session.status, 'active')
        self.assertIn('empatizar', session.stages)

        # Paso 2: abrir la vista del sprint (GET)
        response = self.client.get(reverse('sprint_session', args=[session.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['session'], session)

        # Paso 3: iniciar ejecución del agente (POST start)
        response = self.client.post(reverse('sprint_session', args=[session.pk]), {
            'action': 'start',
            'problema': 'Definir el problema del sprint',
            'usuario': 'Estudiantes universitarios',
            'dolores': 'Falta de herramientas de planificación',
            'idea': 'App de gestión ágil',
            'selected_techniques': json.dumps(['ltg']),
            'technique_prompts': '{}',
            'technique_llm_providers': '{}',
            'language': 'español',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['estado'], 'review')

        # La sesión sigue activa (no ha terminado)
        session.refresh_from_db()
        self.assertEqual(session.status, 'active')

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_END_STATE)
    def test_approve_last_technique_completes_session(self, mock_exec, mock_state):
        session = SprintSession.objects.create(
            user=self.user, name='Sprint Fin', stages=['empatizar'],
        )
        response = self.client.post(
            reverse('sprint_session', args=[session.pk]),
            {'action': 'approve'},
        )
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.status, 'completed')
        self.assertEqual(response.json()['data']['estado'], 'END')

    @patch('llm.views.get_session_state', return_value=_END_STATE)
    def test_completed_session_can_be_exported(self, mock_state):
        session = SprintSession.objects.create(
            user=self.user, name='Sprint Export', status='completed',
        )
        response = self.client.get(reverse('export_session', args=[session.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])
        data = json.loads(response.content)
        self.assertEqual(data['session']['name'], 'Sprint Export')
        self.assertIn('ltg', data['technique_outputs'])

    def test_delete_session_removes_from_listing(self):
        session = SprintSession.objects.create(user=self.user, name='Para Borrar')
        self.client.delete(reverse('delete_session', args=[session.pk]))
        response = self.client.get(reverse('dashboard'))
        names = [s.name for s in response.context['sessions']]
        self.assertNotIn('Para Borrar', names)
        self.assertFalse(SprintSession.objects.filter(pk=session.pk).exists())


# ── Aislamiento multi-usuario ─────────────────────────────────────────────────

class TestMultiUserIsolation(TestCase):
    """
    Verifica que los datos de un usuario son inaccesibles para otro.
    """

    def setUp(self):
        self.user_a = User.objects.create_user(
            username='user_a', email='a@test.com', password='PassA123!',
        )
        self.user_b = User.objects.create_user(
            username='user_b', email='b@test.com', password='PassB123!',
        )
        self.session_a = SprintSession.objects.create(
            user=self.user_a, name='Sesión de A',
        )

    def test_user_b_cannot_view_user_a_session(self):
        self.client.force_login(self.user_b)
        response = self.client.get(
            reverse('sprint_session', args=[self.session_a.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_user_b_cannot_delete_user_a_session(self):
        self.client.force_login(self.user_b)
        response = self.client.delete(
            reverse('delete_session', args=[self.session_a.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(SprintSession.objects.filter(pk=self.session_a.pk).exists())

    def test_user_b_cannot_export_user_a_session(self):
        self.client.force_login(self.user_b)
        response = self.client.get(
            reverse('export_session', args=[self.session_a.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_dashboard_only_shows_own_sessions(self):
        SprintSession.objects.create(user=self.user_b, name='Sesión de B')
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('dashboard'))
        names = [s.name for s in response.context['sessions']]
        self.assertIn('Sesión de A', names)
        self.assertNotIn('Sesión de B', names)

    def test_unauthenticated_user_redirected_from_dashboard(self):
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(
            response, '/user/login/?next=/dashboard/',
            fetch_redirect_response=False,
        )


# ── Gestión de técnicas (admin vs usuario) ────────────────────────────────────

class TestTechniqueManagementIntegration(TestCase):
    """
    Verifica el ciclo completo de gestión de técnicas:
    admin crea → usuarios la ven → admin borra → usuarios ya no la ven.
    """

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_integ', email='admin@test.com',
            password='AdminPass123!', is_staff=True,
        )
        self.user = User.objects.create_user(
            username='user_integ2', email='user2@test.com', password='Pass123!',
        )

    def test_admin_creates_technique_visible_in_catalog(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse('technique_create'),
            data=json.dumps({
                'tech_id': 'nueva-tecnica',
                'name': 'Nueva Técnica',
                'default_prompt': 'Genera algo útil.',
                'stage': 'idear',
            }),
            content_type='application/json',
        )
        # El usuario normal la ve en el catálogo
        self.client.force_login(self.user)
        response = self.client.get(reverse('catalog'))
        tech_ids = [t['tech_id'] for t in response.context['techniques']]
        self.assertIn('nueva-tecnica', tech_ids)

    def test_admin_deletes_custom_then_not_in_catalog(self):
        Technique.objects.create(
            tech_id='temp-tech', name='Temporal',
            default_prompt='Test', is_builtin=False,
        )
        self.client.force_login(self.admin)
        self.client.delete(reverse('technique_delete', args=['temp-tech']))

        self.client.force_login(self.user)
        response = self.client.get(reverse('catalog'))
        tech_ids = [t['tech_id'] for t in response.context['techniques']]
        self.assertNotIn('temp-tech', tech_ids)

    def test_builtin_technique_survives_admin_delete_attempt(self):
        Technique.objects.create(
            tech_id='builtin-tech', name='Builtin',
            default_prompt='Test', is_builtin=True,
        )
        self.client.force_login(self.admin)
        self.client.delete(reverse('technique_delete', args=['builtin-tech']))

        self.client.force_login(self.user)
        response = self.client.get(reverse('catalog'))
        tech_ids = [t['tech_id'] for t in response.context['techniques']]
        self.assertIn('builtin-tech', tech_ids)

    def test_technique_list_api_returns_all(self):
        Technique.objects.create(
            tech_id='api-tech', name='API Tech',
            default_prompt='Test', is_builtin=False,
        )
        response = self.client.get(reverse('technique_list'))
        self.assertEqual(response.status_code, 200)
        tech_ids = [t['tech_id'] for t in response.json()['techniques']]
        self.assertIn('api-tech', tech_ids)


# ── Flujo de feedback e historial ─────────────────────────────────────────────

class TestFeedbackAndReanalysisFlow(TestCase):
    """
    Verifica que el ciclo feedback → reanalysis → approve funciona
    y que la sesión solo se cierra al aprobar, no al pedir feedback.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='user_feedback', email='fb@test.com', password='Pass123!',
        )
        self.client.force_login(self.user)
        self.session = SprintSession.objects.create(
            user=self.user, name='Feedback Sprint',
        )

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_REVIEW_STATE)
    def test_feedback_does_not_complete_session(self, mock_exec, mock_state):
        self.client.post(
            reverse('sprint_session', args=[self.session.pk]),
            {'action': 'feedback', 'feedback': 'Amplía los riesgos'},
        )
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'active')

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint')
    def test_multiple_feedback_then_approve_completes_session(self, mock_exec, mock_state):
        mock_exec.return_value = _REVIEW_STATE
        self.client.post(
            reverse('sprint_session', args=[self.session.pk]),
            {'action': 'feedback', 'feedback': 'Primera revisión'},
        )
        self.client.post(
            reverse('sprint_session', args=[self.session.pk]),
            {'action': 'feedback', 'feedback': 'Segunda revisión'},
        )
        mock_exec.return_value = _END_STATE
        self.client.post(
            reverse('sprint_session', args=[self.session.pk]),
            {'action': 'approve'},
        )
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'completed')
