"""
Pruebas de rendimiento con Locust.

Instalación:  pip install locust
Ejecución:    locust -f locustfile.py --host http://localhost:8000
              Luego abrir http://localhost:8089 y configurar usuarios/rampa.

O headless:   locust -f locustfile.py --host http://localhost:8000
              --users 20 --spawn-rate 2 --run-time 60s --headless

Requisito: servidor Django corriendo con usuario test_perf creado.
Crear con: docker exec django_web python manage.py seed_tests
"""
import json
import random
from locust import HttpUser, task, between


# ── Usuario base con autenticación y CSRF ────────────────────────────────────

class _AuthBase(HttpUser):
    abstract = True

    def on_start(self):
        # GET login para obtener cookie csrftoken
        self.client.get('/user/login/')
        csrf = self.client.cookies.get('csrftoken', '')
        self.client.post(
            '/user/login/',
            data={
                'username': 'test_perf',
                'password': 'PerfPass123!',
                'csrfmiddlewaretoken': csrf,
            },
            headers={'Referer': f'{self.host}/user/login/'},
            allow_redirects=True,
        )
        self.session_id = self._create_session()

    def _csrf(self):
        return self.client.cookies.get('csrftoken', '')

    def _create_session(self) -> int | None:
        csrf = self._csrf()
        r = self.client.post(
            '/dashboard/',
            data={
                'name': f'Perf Session {random.randint(1000, 9999)}',
                'description': 'Prueba de carga',
                'stages': ['empatizar'],
                'csrfmiddlewaretoken': csrf,
            },
            headers={'Referer': f'{self.host}/dashboard/'},
            allow_redirects=False,
        )
        if r.status_code == 302:
            location = r.headers.get('Location', '')
            try:
                return int(location.rstrip('/').split('/')[-1])
            except (ValueError, IndexError):
                pass
        return None

    def on_stop(self):
        if self.session_id:
            csrf = self._csrf()
            self.client.delete(
                f'/sprint/{self.session_id}/delete/',
                headers={'X-CSRFToken': csrf},
            )


# ── Escenario 1: Usuario que navega (lectura) ─────────────────────────────────

class BrowseUser(_AuthBase):
    """Simula mayoría del tráfico: navegación y lectura."""
    weight = 3
    wait_time = between(1, 3)

    @task(4)
    def view_dashboard(self):
        with self.client.get('/dashboard/', catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"Dashboard {r.status_code}")

    @task(3)
    def view_catalog(self):
        with self.client.get('/catalog/', catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"Catalog {r.status_code}")

    @task(2)
    def list_techniques_api(self):
        with self.client.get('/sprint/techniques/', catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"Techniques API {r.status_code}")
            elif 'techniques' not in r.json():
                r.failure("Missing 'techniques' key")

    @task(2)
    def open_sprint(self):
        if not self.session_id:
            return
        with self.client.get(f'/sprint/{self.session_id}/', catch_response=True) as r:
            if r.status_code == 404:
                r.success()
            elif r.status_code != 200:
                r.failure(f"Sprint view {r.status_code}")

    @task(1)
    def view_profile(self):
        with self.client.get('/user/profile/', catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"Profile {r.status_code}")


# ── Escenario 2: Usuario que crea y gestiona sesiones ─────────────────────────

class SessionManagerUser(_AuthBase):
    """Crea y borra sesiones bajo carga."""
    weight = 1
    wait_time = between(2, 5)

    @task(3)
    def create_and_delete_session(self):
        csrf = self._csrf()
        r = self.client.post(
            '/dashboard/',
            data={
                'name': f'Tmp {random.randint(10000, 99999)}',
                'description': 'Load test',
                'csrfmiddlewaretoken': csrf,
            },
            headers={'Referer': f'{self.host}/dashboard/'},
            allow_redirects=False,
        )
        if r.status_code == 302:
            location = r.headers.get('Location', '')
            try:
                sid = int(location.rstrip('/').split('/')[-1])
                self.client.delete(
                    f'/sprint/{sid}/delete/',
                    headers={'X-CSRFToken': self._csrf()},
                )
            except (ValueError, IndexError):
                pass

    @task(1)
    def view_dashboard(self):
        with self.client.get('/dashboard/', catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"Dashboard {r.status_code}")


# ── Escenario 3: Administrador gestionando técnicas ───────────────────────────

class AdminUser(_AuthBase):
    """Crea y borra técnicas personalizadas (requiere is_staff en test_perf)."""
    weight = 1
    wait_time = between(3, 8)

    @task
    def create_and_delete_technique(self):
        csrf = self._csrf()
        tech_id = f'perf-{random.randint(10000, 99999)}'
        with self.client.post(
            '/sprint/techniques/create/',
            data=json.dumps({
                'tech_id': tech_id,
                'name': f'Perf Tech {tech_id}',
                'default_prompt': 'Generate output.',
                'stage': 'idear',
            }),
            headers={
                'X-CSRFToken': csrf,
                'Content-Type': 'application/json',
            },
            catch_response=True,
        ) as r:
            if r.status_code == 200 and r.json().get('ok'):
                self.client.delete(
                    f'/sprint/techniques/{tech_id}/delete/',
                    headers={'X-CSRFToken': self._csrf()},
                )
            elif r.status_code == 403:
                r.success()
            else:
                r.failure(f"Technique create {r.status_code}: {r.text[:100]}")
