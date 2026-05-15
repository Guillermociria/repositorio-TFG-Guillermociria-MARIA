"""
Configuración de Playwright + Django.

Instalación:
    pip install pytest pytest-playwright pytest-django
    playwright install chromium

Ejecución (desde la raíz del repo):
    pytest tests_playwright/ -v

Requiere: servidor Django corriendo en BASE_URL (por defecto localhost:8000).
Crear usuario de test con:
    python maria/manage.py shell -c "
        from user.models import User
        User.objects.create_user('pw_test', 'pw@test.com', 'PwPass123!')
    "
"""
import os
import pytest

BASE_URL = os.getenv('DJANGO_BASE_URL', 'http://localhost:8000')
TEST_USER = os.getenv('PW_TEST_USER', 'pw_test')
TEST_PASS = os.getenv('PW_TEST_PASS', 'PwPass123!')


@pytest.fixture(scope='session')
def base_url():
    return BASE_URL


@pytest.fixture
def logged_page(page, base_url):
    """Página con sesión ya iniciada."""
    page.goto(f'{base_url}/user/login/')
    page.fill('input[name="username"]', TEST_USER)
    page.fill('input[name="password"]', TEST_PASS)
    page.click('button[type="submit"]')
    page.wait_for_url(f'{base_url}/dashboard/')
    return page
