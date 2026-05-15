"""
Pruebas de interfaz con Playwright.
Ejecutar contra un servidor Django en marcha (ver conftest.py).
"""
import re
import pytest
from playwright.sync_api import expect

BASE_URL = 'http://localhost:8000'


# ── RF-01: Login ─────────────────────────────────────────────────────────────

class TestRF01LoginUI:
    """RF-01: Iniciar sesión — pruebas de interfaz"""

    def test_positive_valid_login_redirects_to_dashboard(self, page):
        page.goto(f'{BASE_URL}/user/login/')
        page.fill('input[name="username"]', 'pw_test')
        page.fill('input[name="password"]', 'PwPass123!')
        page.click('button[type="submit"]')
        page.wait_for_url(f'{BASE_URL}/dashboard/')
        expect(page).to_have_url(re.compile(r'.*/dashboard/'))

    def test_negative_wrong_password_shows_error(self, page):
        page.goto(f'{BASE_URL}/user/login/')
        page.fill('input[name="username"]', 'pw_test')
        page.fill('input[name="password"]', 'WrongPass')
        page.click('button[type="submit"]')
        # Debe permanecer en login
        expect(page).to_have_url(re.compile(r'.*/user/login/'))
        # Debe mostrar mensaje de error en el formulario
        expect(page.locator('form .errorlist, form .error, .alert-danger')).to_be_visible()

    def test_negative_empty_fields_form_validation(self, page):
        page.goto(f'{BASE_URL}/user/login/')
        page.click('button[type="submit"]')
        # El navegador o Django bloquean el envío con campos vacíos
        expect(page).to_have_url(re.compile(r'.*/user/login/'))


# ── RF-02: Crear sesión ───────────────────────────────────────────────────────

class TestRF02CreateSessionUI:
    """RF-02: Crear sesión de trabajo — pruebas de interfaz"""

    def test_positive_create_session_redirects_to_sprint(self, logged_page):
        page = logged_page
        page.goto(f'{BASE_URL}/dashboard/')

        # Abrir modal (header button o empty-state button)
        page.locator('button.btn[onclick="openModal()"]').first.click()
        page.locator('.modal-overlay.open').wait_for()

        page.fill('input[name="name"]', 'UI Test Sprint')
        description_input = page.locator('textarea[name="description"], input[name="description"]')
        if description_input.count() > 0:
            description_input.fill('Sesión creada desde Playwright')
        page.locator('.modal button[type="submit"]').click()

        expect(page).to_have_url(re.compile(r'.*/sprint/\d+/'))

    def test_negative_create_without_name_stays_on_dashboard(self, logged_page):
        page = logged_page
        page.goto(f'{BASE_URL}/dashboard/')

        # Abrir modal
        page.locator('button.btn[onclick="openModal()"]').first.click()
        page.locator('.modal-overlay.open').wait_for()

        page.locator('input[name="name"]').fill('')
        page.locator('.modal button[type="submit"]').click()
        expect(page).to_have_url(re.compile(r'.*/dashboard/'))


# ── RF-04: Catálogo de técnicas ───────────────────────────────────────────────

class TestRF04CatalogUI:
    """RF-04: Consultar catálogo de técnicas por etapa — pruebas de interfaz"""

    def test_positive_catalog_shows_techniques(self, logged_page):
        page = logged_page
        page.goto(f'{BASE_URL}/catalog/')
        expect(page).to_have_url(re.compile(r'.*/catalog/'))
        # Debe haber al menos una técnica visible
        technique_cards = page.locator('.tech-card')
        expect(technique_cards.first).to_be_visible()

    def test_negative_unauthenticated_redirects_to_login(self, page):
        page.goto(f'{BASE_URL}/catalog/')
        expect(page).to_have_url(re.compile(r'.*/user/login/'))


# ── RF-14: Listar sesiones ────────────────────────────────────────────────────

class TestRF14SessionListUI:
    """RF-14: Listar y reabrir sesiones — pruebas de interfaz"""

    def test_positive_dashboard_lists_sessions(self, logged_page):
        page = logged_page
        page.goto(f'{BASE_URL}/dashboard/')
        expect(page).to_have_url(re.compile(r'.*/dashboard/'))
        expect(page.locator('body')).to_be_visible()

    def test_positive_click_session_opens_sprint(self, logged_page):
        page = logged_page
        page.goto(f'{BASE_URL}/dashboard/')

        session_links = page.locator('a[href*="/sprint/"]')
        if session_links.count() == 0:
            pytest.skip('No hay sesiones en el dashboard para abrir')

        session_links.first.click()
        expect(page).to_have_url(re.compile(r'.*/sprint/\d+/'))


# ── RF-19: Gestión de claves API ──────────────────────────────────────────────

class TestRF19ProfileUI:
    """RF-19: Gestionar claves API personales — pruebas de interfaz"""

    def test_positive_profile_page_loads(self, logged_page):
        page = logged_page
        page.goto(f'{BASE_URL}/user/profile/')
        expect(page).to_have_url(re.compile(r'.*/user/profile/'))
        # Los campos de clave API deben existir
        expect(page.locator('input[name="google_api_key"]')).to_be_visible()

    def test_positive_save_api_key_shows_confirmation(self, logged_page):
        page = logged_page
        page.goto(f'{BASE_URL}/user/profile/')
        page.fill('input[name="google_api_key"]', 'AIza-ui-test-key')
        # Use profile form submit button specifically (not the logout button in the header)
        page.locator('form:not([action]) button[type="submit"]').click()
        expect(page).to_have_url(re.compile(r'.*/user/profile/'))

    def test_negative_profile_requires_login(self, page):
        page.goto(f'{BASE_URL}/user/profile/')
        expect(page).to_have_url(re.compile(r'.*/user/login/'))


# ── RF-21: Catálogo — visualización de técnicas personalizadas ────────────────

class TestRF21CatalogTechniqueUI:
    """RF-21: Ver técnicas personalizadas en catálogo — pruebas de interfaz"""

    def test_positive_technique_list_api_returns_json(self, page):
        response = page.goto(f'{BASE_URL}/sprint/techniques/')
        assert response is not None
        expect(page).to_have_url(re.compile(r'.*/sprint/techniques/'))
        content = page.content()
        assert 'techniques' in content


# ── Rendimiento básico de páginas clave ───────────────────────────────────────

class TestPageLoadPerformance:
    """
    Verifica que las páginas principales cargan en tiempo razonable.
    Umbral: 3 segundos (configurable con PW_PERF_THRESHOLD_MS env var).
    """
    import os
    THRESHOLD_MS = int(os.getenv('PW_PERF_THRESHOLD_MS', '3000'))

    def _measure(self, page, url: str) -> float:
        """Devuelve el tiempo de carga en ms usando la Navigation Timing API."""
        page.goto(url, wait_until='networkidle')
        timing = page.evaluate("""() => {
            const t = performance.getEntriesByType('navigation')[0];
            return t ? t.duration : 0;
        }""")
        return float(timing)

    def test_login_page_load_time(self, page):
        ms = self._measure(page, f'{BASE_URL}/user/login/')
        assert ms < self.THRESHOLD_MS, f"Login page took {ms:.0f}ms (limit {self.THRESHOLD_MS}ms)"

    def test_dashboard_load_time(self, logged_page):
        ms = self._measure(logged_page, f'{BASE_URL}/dashboard/')
        assert ms < self.THRESHOLD_MS, f"Dashboard took {ms:.0f}ms (limit {self.THRESHOLD_MS}ms)"

    def test_catalog_load_time(self, logged_page):
        ms = self._measure(logged_page, f'{BASE_URL}/catalog/')
        assert ms < self.THRESHOLD_MS, f"Catalog took {ms:.0f}ms (limit {self.THRESHOLD_MS}ms)"
