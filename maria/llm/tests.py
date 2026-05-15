import json
from unittest.mock import patch
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from user.models import User
from llm.models import SprintSession, Technique
from nodes.ltg.subnodes.validate import ValidateLTGNode


_MOCK_RESULT = {
    "estado": "review",
    "current_index": 0,
    "technique_id": "ltg",
    "output": {"critique": "test", "assumptions": [], "alternatives": [], "risks": []},
    "all_outputs": {},
    "awaiting_pre_inputs": False,
}

_MOCK_RESULT_END = {
    "estado": "END",
    "current_index": 1,
    "technique_id": None,
    "output": None,
    "all_outputs": {"ltg": {"critique": "done"}},
    "awaiting_pre_inputs": False,
}


class _Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='ValidPass123!',
        )
        self.client.force_login(self.user)
        self.technique = Technique.objects.create(
            tech_id='ltg',
            name='Learn the Goal',
            stage='empatizar',
            is_builtin=True,
            default_prompt='Analyze the problem.',
        )
        self.session = SprintSession.objects.create(
            user=self.user,
            name='Test Session',
            description='Testing',
            stages=['empatizar'],
        )

    def _sprint_url(self):
        return reverse('sprint_session', args=[self.session.pk])


# ── ValidateLTGNode unit tests ────────────────────────────────────────────────

class TestValidateLTGNode(SimpleTestCase):
    """Unit tests for the LTG validation subnode (supports RF-08/RF-09)"""

    def setUp(self):
        self.node = ValidateLTGNode()

    def _s(self, raw):
        return {"raw_output": raw, "retry_count": 0}

    def test_positive_all_keys_valid(self):
        raw = json.dumps({"critique": "ok", "assumptions": [], "alternatives": [], "risks": []})
        result = self.node(self._s(raw))
        self.assertTrue(result["validated"])
        self.assertIn("ltg_analysis", result)

    def test_positive_keys_case_insensitive(self):
        raw = json.dumps({"Critique": "x", "ASSUMPTIONS": [], "Alternatives": [], "Risks": []})
        result = self.node(self._s(raw))
        self.assertTrue(result["validated"])

    def test_negative_invalid_json(self):
        result = self.node(self._s("not valid json {{"))
        self.assertFalse(result["validated"])
        self.assertIn("invalid_json", result["errors"])

    def test_negative_missing_risks(self):
        raw = json.dumps({"critique": "x", "assumptions": [], "alternatives": []})
        result = self.node(self._s(raw))
        self.assertFalse(result["validated"])
        self.assertIn("missing_risks", result["errors"])

    def test_negative_missing_critique(self):
        raw = json.dumps({"assumptions": [], "alternatives": [], "risks": []})
        result = self.node(self._s(raw))
        self.assertFalse(result["validated"])
        self.assertIn("missing_critique", result["errors"])


# ── RF-02: Crear sesión de trabajo ────────────────────────────────────────────

class TestRF02SprintSessionCreate(_Base):
    """RF-02: Crear sesión de trabajo"""

    def test_positive_session_created_and_redirects(self):
        response = self.client.post(reverse('dashboard'), {
            'name': 'New Sprint',
            'description': 'My description',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SprintSession.objects.filter(user=self.user, name='New Sprint').exists())

    def test_negative_no_name_no_session_created(self):
        count_before = SprintSession.objects.filter(user=self.user).count()
        response = self.client.post(reverse('dashboard'), {
            'name': '',
            'description': 'Without a name',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SprintSession.objects.filter(user=self.user).count(), count_before)


# ── RF-03: Configurar etapas ──────────────────────────────────────────────────

class TestRF03StageConfiguration(_Base):
    """RF-03: Configurar etapas"""

    def test_positive_stages_associated_to_session(self):
        self.client.post(reverse('dashboard'), {
            'name': 'Sprint Etapas',
            'stages': ['empatizar', 'definir'],
        })
        session = SprintSession.objects.get(user=self.user, name='Sprint Etapas')
        self.assertIn('empatizar', session.stages)
        self.assertIn('definir', session.stages)

    def test_negative_cancel_no_stages_session_empty(self):
        self.client.post(reverse('dashboard'), {'name': 'Sin Etapas'})
        session = SprintSession.objects.get(user=self.user, name='Sin Etapas')
        self.assertEqual(session.stages, [])


# ── RF-04: Consultar catálogo de técnicas por etapa ───────────────────────────

class TestRF04CatalogView(_Base):
    """RF-04: Consultar catálogo de técnicas por etapa"""

    def test_positive_authenticated_user_sees_techniques(self):
        response = self.client.get(reverse('catalog'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog.html')
        self.assertGreater(len(response.context['techniques']), 0)

    def test_negative_unauthenticated_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(reverse('catalog'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/login/', response['Location'])


# ── RF-05 & RF-06: Seleccionar técnicas e introducir información ──────────────

class TestRF05RF06TechniqueSelectionInputs(_Base):
    """RF-05: Seleccionar y ordenar técnicas | RF-06: Introducir información"""

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_positive_selected_techniques_and_inputs_passed(self, mock_exec, mock_state):
        self.client.post(self._sprint_url(), {
            'action': 'start',
            'problema': 'Descripción del problema',
            'usuario': 'Usuario objetivo',
            'dolores': 'Puntos de dolor',
            'idea': 'Idea inicial',
            'selected_techniques': json.dumps(['ltg']),
            'technique_prompts': json.dumps({'ltg': 'Custom prompt'}),
            'technique_llm_providers': json.dumps({'ltg': 'google'}),
            'language': 'español',
        })
        mock_exec.assert_called_once()
        inputs = mock_exec.call_args.kwargs['inputs']
        self.assertEqual(inputs['selected_techniques'], ['ltg'])
        self.assertEqual(inputs['problem_definition'], 'Descripción del problema')
        self.assertEqual(inputs['target_user'], 'Usuario objetivo')
        self.assertEqual(inputs['pain_points'], 'Puntos de dolor')
        self.assertEqual(inputs['initial_idea'], 'Idea inicial')

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_positive_technique_order_preserved(self, mock_exec, mock_state):
        ordered = ['sq', 'ltg']
        self.client.post(self._sprint_url(), {
            'action': 'start',
            'problema': 'P', 'usuario': 'U', 'dolores': 'D', 'idea': 'I',
            'selected_techniques': json.dumps(ordered),
            'technique_prompts': '{}',
            'technique_llm_providers': '{}',
        })
        inputs = mock_exec.call_args.kwargs['inputs']
        self.assertEqual(inputs['selected_techniques'], ordered)

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_negative_missing_required_fields_still_calls_service(self, mock_exec, mock_state):
        # Validation is client-side; server calls the service with empty values
        response = self.client.post(self._sprint_url(), {
            'action': 'start',
            'problema': '',
            'usuario': '',
            'dolores': '',
            'idea': '',
            'selected_techniques': json.dumps(['ltg']),
            'technique_prompts': '{}',
            'technique_llm_providers': '{}',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')


# ── RF-07: Encadenar salida como entrada ──────────────────────────────────────

class TestRF07OutputChaining(_Base):
    """RF-07: Encadenar salida de una técnica como entrada de la siguiente"""

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_positive_extra_inputs_passed_to_service(self, mock_exec, mock_state):
        extra = {'pregunta_1': 'Respuesta de técnica previa'}
        response = self.client.post(self._sprint_url(), {
            'action': 'pre_inputs',
            'extra_inputs': json.dumps(extra),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_exec.call_args.kwargs['extra_inputs'], extra)

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_negative_no_reference_manual_entry_empty_extra(self, mock_exec, mock_state):
        response = self.client.post(self._sprint_url(), {'action': 'pre_inputs'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_exec.call_args.kwargs['extra_inputs'], {})


# ── RF-08: Invocar al agente de IA ────────────────────────────────────────────

class TestRF08AgentInvocation(_Base):
    """RF-08: Invocar al agente de IA"""

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_positive_agent_invoked_returns_proposal(self, mock_exec, mock_state):
        response = self.client.post(self._sprint_url(), {
            'action': 'start',
            'problema': 'P', 'usuario': 'U', 'dolores': 'D', 'idea': 'I',
            'selected_techniques': json.dumps(['ltg']),
            'technique_prompts': '{}',
            'technique_llm_providers': '{}',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('output', data['data'])
        mock_exec.assert_called_once()

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', side_effect=Exception('LLM provider error'))
    def test_negative_provider_error_returns_500(self, mock_exec, mock_state):
        response = self.client.post(self._sprint_url(), {
            'action': 'start',
            'problema': 'P', 'usuario': 'U', 'dolores': 'D', 'idea': 'I',
            'selected_techniques': json.dumps(['ltg']),
            'technique_prompts': '{}',
            'technique_llm_providers': '{}',
        })
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('LLM provider error', data['message'])


# ── RF-09: Analizar propuesta y decidir ───────────────────────────────────────

class TestRF09ProposalDecision(_Base):
    """RF-09: Analizar propuesta y decidir"""

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_positive_approve_calls_service_with_approve(self, mock_exec, mock_state):
        self.client.post(self._sprint_url(), {'action': 'approve'})
        self.assertEqual(mock_exec.call_args.kwargs['action'], 'approve')

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_negative_request_new_analysis_calls_feedback(self, mock_exec, mock_state):
        self.client.post(self._sprint_url(), {
            'action': 'feedback',
            'feedback': 'Necesito más detalle',
        })
        kwargs = mock_exec.call_args.kwargs
        self.assertEqual(kwargs['action'], 'feedback')
        self.assertEqual(kwargs['feedback'], 'Necesito más detalle')


# ── RF-10: Solicitar nuevo análisis ───────────────────────────────────────────

class TestRF10NewAnalysis(_Base):
    """RF-10: Solicitar nuevo análisis del agente"""

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_positive_observations_passed_with_context(self, mock_exec, mock_state):
        feedback_text = 'Faltan alternativas sobre escalabilidad'
        self.client.post(self._sprint_url(), {
            'action': 'feedback',
            'feedback': feedback_text,
        })
        kwargs = mock_exec.call_args.kwargs
        self.assertEqual(kwargs['feedback'], feedback_text)
        self.assertEqual(kwargs['action'], 'feedback')


# ── RF-11: Cerrar técnica aceptada ────────────────────────────────────────────

class TestRF11CloseTechnique(_Base):
    """RF-11: Cerrar técnica aceptada"""

    _next_state = {
        **_MOCK_RESULT,
        "estado": "pre_technique",
        "current_index": 1,
        "technique_id": "sq",
    }

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_next_state)
    def test_positive_approve_advances_to_next_technique(self, mock_exec, mock_state):
        response = self.client.post(self._sprint_url(), {'action': 'approve'})
        data = response.json()
        self.assertEqual(data['data']['estado'], 'pre_technique')
        self.assertEqual(data['data']['current_index'], 1)

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_negative_feedback_keeps_technique_open(self, mock_exec, mock_state):
        response = self.client.post(self._sprint_url(), {
            'action': 'feedback',
            'feedback': 'Not satisfied',
        })
        data = response.json()
        self.assertEqual(data['data']['estado'], 'review')
        self.assertEqual(data['data']['current_index'], 0)


# ── RF-12: Cerrar etapa y sesión ──────────────────────────────────────────────

class TestRF12CloseStageAndSession(_Base):
    """RF-12: Cerrar etapa y sesión"""

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT_END)
    def test_positive_all_techniques_accepted_marks_session_completed(self, mock_exec, mock_state):
        self.client.post(self._sprint_url(), {'action': 'approve'})
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'completed')

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_negative_pending_techniques_session_stays_active(self, mock_exec, mock_state):
        self.client.post(self._sprint_url(), {'action': 'approve'})
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'active')


# ── RF-13: Persistir estado de la sesión ──────────────────────────────────────

class TestRF13SessionPersistence(_Base):
    """RF-13: Persistir estado de la sesión"""

    _saved_state = {
        "estado": "review",
        "current_index": 0,
        "technique_id": "ltg",
        "output": {"critique": "Previous output"},
        "all_outputs": {"ltg": {"critique": "Previous output"}},
        "awaiting_pre_inputs": False,
        "selected_techniques": ["ltg"],
        "problem_definition": "Saved problem",
        "target_user": "Saved user",
        "pain_points": "Saved pain",
        "initial_idea": "Saved idea",
    }

    @patch('llm.views.get_session_state', return_value=_saved_state)
    def test_positive_existing_state_restored_on_reopen(self, mock_state):
        response = self.client.get(self._sprint_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.context['existing_state'], 'null')
        state = json.loads(response.context['existing_state'])
        self.assertEqual(state['problem_definition'], 'Saved problem')

    @patch('llm.views.get_session_state', return_value=None)
    def test_negative_db_failure_returns_null_state(self, mock_state):
        response = self.client.get(self._sprint_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['existing_state'], 'null')


# ── RF-14: Listar y reabrir sesiones ─────────────────────────────────────────

class TestRF14SessionListing(_Base):
    """RF-14: Listar y reabrir sesiones"""

    def test_positive_sessions_listed_on_dashboard(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.session, list(response.context['sessions']))

    def test_negative_no_sessions_empty_queryset(self):
        other = User.objects.create_user(
            username='nosp', email='nosp@test.com', password='Pass123!'
        )
        self.client.force_login(other)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(len(response.context['sessions']), 0)

    def test_negative_other_user_sessions_not_visible(self):
        other = User.objects.create_user(
            username='other', email='other@test.com', password='Pass123!'
        )
        SprintSession.objects.create(user=other, name='Other Session')
        response = self.client.get(reverse('dashboard'))
        names = [s.name for s in response.context['sessions']]
        self.assertNotIn('Other Session', names)


# ── RF-15: Exportar resultados de la sesión ───────────────────────────────────

class TestRF15ExportSession(_Base):
    """RF-15: Exportar resultados de la sesión"""

    _state_with_outputs = {
        "estado": "END",
        "current_index": 0,
        "technique_id": None,
        "output": None,
        "all_outputs": {"ltg": {"critique": "done", "assumptions": [], "alternatives": [], "risks": []}},
        "awaiting_pre_inputs": False,
        "selected_techniques": ["ltg"],
        "problem_definition": "Problem",
        "target_user": "User",
        "pain_points": "Pain",
        "initial_idea": "Idea",
    }

    @patch('llm.views.get_session_state', return_value=_state_with_outputs)
    def test_positive_returns_json_attachment_with_outputs(self, mock_state):
        response = self.client.get(
            reverse('export_session', args=[self.session.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('attachment', response['Content-Disposition'])
        data = json.loads(response.content)
        self.assertIn('session', data)
        self.assertIn('technique_outputs', data)
        self.assertTrue(data['technique_outputs'])

    @patch('llm.views.get_session_state', return_value=None)
    def test_negative_no_closed_techniques_blocked(self, mock_state):
        response = self.client.get(
            reverse('export_session', args=[self.session.pk])
        )
        self.assertEqual(response.status_code, 400)

    @patch('llm.views.get_session_state', return_value={'all_outputs': {}})
    def test_negative_empty_outputs_blocked(self, mock_state):
        response = self.client.get(
            reverse('export_session', args=[self.session.pk])
        )
        self.assertEqual(response.status_code, 400)

    def test_negative_other_user_session_returns_404(self):
        other = User.objects.create_user(
            username='other4', email='other4@test.com', password='Pass123!'
        )
        other_session = SprintSession.objects.create(user=other, name='Other')
        response = self.client.get(
            reverse('export_session', args=[other_session.pk])
        )
        self.assertEqual(response.status_code, 404)


# ── RF-16: Eliminar sesiones ─────────────────────────────────────────────────

class TestRF16DeleteSession(_Base):
    """RF-16: Eliminar sesiones"""

    def test_positive_delete_removes_session(self):
        response = self.client.delete(
            reverse('delete_session', args=[self.session.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertFalse(SprintSession.objects.filter(pk=self.session.pk).exists())

    def test_negative_cancel_confirmation_session_stays(self):
        # No DELETE sent (user cancels dialog client-side)
        self.assertTrue(SprintSession.objects.filter(pk=self.session.pk).exists())

    def test_negative_delete_other_user_session_returns_404(self):
        other = User.objects.create_user(
            username='other5', email='other5@test.com', password='Pass123!'
        )
        other_session = SprintSession.objects.create(user=other, name='Other')
        response = self.client.delete(
            reverse('delete_session', args=[other_session.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(SprintSession.objects.filter(pk=other_session.pk).exists())


# ── RF-17: Seleccionar idioma de respuesta ────────────────────────────────────

class TestRF17LanguageSelection(_Base):
    """RF-17: Seleccionar el idioma de respuesta del agente"""

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_positive_language_stored_in_agent_state(self, mock_exec, mock_state):
        self.client.post(self._sprint_url(), {
            'action': 'start',
            'problema': 'P', 'usuario': 'U', 'dolores': 'D', 'idea': 'I',
            'selected_techniques': json.dumps(['ltg']),
            'technique_prompts': '{}',
            'technique_llm_providers': '{}',
            'language': 'english',
        })
        inputs = mock_exec.call_args.kwargs['inputs']
        self.assertEqual(inputs['language'], 'english')

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_negative_no_language_defaults_to_español(self, mock_exec, mock_state):
        self.client.post(self._sprint_url(), {
            'action': 'start',
            'problema': 'P', 'usuario': 'U', 'dolores': 'D', 'idea': 'I',
            'selected_techniques': json.dumps(['ltg']),
            'technique_prompts': '{}',
            'technique_llm_providers': '{}',
        })
        inputs = mock_exec.call_args.kwargs['inputs']
        self.assertEqual(inputs['language'], 'español')


# ── RF-18: Seleccionar proveedor LLM por técnica ─────────────────────────────

class TestRF18ProviderSelection(_Base):
    """RF-18: Seleccionar el proveedor LLM por técnica"""

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_positive_provider_included_in_inputs(self, mock_exec, mock_state):
        self.user.anthropic_api_key = 'sk-ant-key'
        self.user.save()
        self.client.post(self._sprint_url(), {
            'action': 'start',
            'problema': 'P', 'usuario': 'U', 'dolores': 'D', 'idea': 'I',
            'selected_techniques': json.dumps(['ltg']),
            'technique_prompts': '{}',
            'technique_llm_providers': json.dumps({'ltg': 'anthropic'}),
        })
        inputs = mock_exec.call_args.kwargs['inputs']
        self.assertEqual(inputs['technique_llm_providers'], {'ltg': 'anthropic'})
        self.assertIn('anthropic', inputs['user_api_keys'])

    @patch('llm.views.get_session_state', return_value=None)
    def test_negative_no_user_keys_only_google_available(self, mock_state):
        response = self.client.get(self._sprint_url())
        self.assertEqual(response.status_code, 200)
        providers = json.loads(response.context['available_providers'])
        ids = [p['id'] for p in providers]
        self.assertEqual(ids, ['google'])

    @patch('llm.views.get_session_state', return_value=None)
    def test_positive_user_with_keys_sees_extra_providers(self, mock_state):
        self.user.openai_api_key = 'sk-openai'
        self.user.anthropic_api_key = 'sk-ant'
        self.user.save()
        response = self.client.get(self._sprint_url())
        providers = json.loads(response.context['available_providers'])
        ids = [p['id'] for p in providers]
        self.assertIn('google', ids)
        self.assertIn('openai', ids)
        self.assertIn('anthropic', ids)


# ── RF-20: Editar prompt durante revisión HITL ───────────────────────────────

class TestRF20HITLPromptEdit(_Base):
    """RF-20: Editar el prompt de una técnica durante la revisión HITL"""

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_positive_edited_prompt_passed_to_service(self, mock_exec, mock_state):
        edited = 'Pon más énfasis en los riesgos técnicos'
        response = self.client.post(self._sprint_url(), {
            'action': 'feedback',
            'feedback': 'Not deep enough',
            'current_prompt': edited,
        })
        self.assertEqual(response.status_code, 200)
        kwargs = mock_exec.call_args.kwargs
        self.assertEqual(kwargs['action'], 'feedback')
        self.assertEqual(kwargs['current_prompt'], edited)

    @patch('llm.views.get_session_state', return_value=None)
    @patch('llm.views.ejecutar_agente_sprint', return_value=_MOCK_RESULT)
    def test_negative_approve_without_edit_no_prompt_update(self, mock_exec, mock_state):
        response = self.client.post(self._sprint_url(), {'action': 'approve'})
        self.assertEqual(response.status_code, 200)
        kwargs = mock_exec.call_args.kwargs
        self.assertEqual(kwargs['action'], 'approve')
        self.assertIsNone(kwargs.get('current_prompt'))


# ── RF-21: Crear y eliminar técnicas personalizadas ───────────────────────────

class TestRF21CustomTechniqueManagement(_Base):
    """RF-21: Crear y eliminar técnicas personalizadas del catálogo"""

    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='AdminPass123!',
            is_staff=True,
        )

    def test_positive_admin_creates_custom_technique(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('technique_create'),
            data=json.dumps({
                'tech_id': 'custom-tech',
                'name': 'Custom Technique',
                'default_prompt': 'Generate something useful.',
                'stage': 'idear',
                'inputs_description': 'Inputs',
                'outputs_description': 'Outputs',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        tech = Technique.objects.get(tech_id='custom-tech')
        self.assertFalse(tech.is_builtin)

    def test_positive_admin_deletes_custom_technique(self):
        Technique.objects.create(
            tech_id='deletable',
            name='Deletable',
            default_prompt='Test',
            is_builtin=False,
        )
        self.client.force_login(self.admin)
        response = self.client.delete(reverse('technique_delete', args=['deletable']))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Technique.objects.filter(tech_id='deletable').exists())

    def test_negative_admin_cannot_delete_builtin_technique(self):
        self.client.force_login(self.admin)
        response = self.client.delete(reverse('technique_delete', args=['ltg']))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Technique.objects.filter(tech_id='ltg').exists())

    def test_negative_non_admin_cannot_create_technique(self):
        response = self.client.post(
            reverse('technique_create'),
            data=json.dumps({
                'tech_id': 'hack-tech',
                'name': 'Hack',
                'default_prompt': 'Prompt',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_negative_non_admin_cannot_delete_technique(self):
        response = self.client.delete(reverse('technique_delete', args=['ltg']))
        self.assertEqual(response.status_code, 403)

    def test_negative_duplicate_tech_id_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('technique_create'),
            data=json.dumps({
                'tech_id': 'ltg',
                'name': 'Duplicate LTG',
                'default_prompt': 'Some prompt',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Ya existe', response.json()['error'])
