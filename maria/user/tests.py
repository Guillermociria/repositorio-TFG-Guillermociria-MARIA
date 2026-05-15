from django.test import TestCase
from django.urls import reverse
from user.models import User


class TestRF01Login(TestCase):
    """RF-01: Iniciar sesión de trabajo"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='ValidPass123!',
        )

    def test_positive_valid_credentials_redirect_to_dashboard(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'ValidPass123!',
        })
        self.assertRedirects(response, '/dashboard/', fetch_redirect_response=False)

    def test_negative_wrong_password_stays_on_login(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'WrongPassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/login.html')
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_negative_nonexistent_user_stays_on_login(self):
        response = self.client.post(reverse('login'), {
            'username': 'noexiste',
            'password': 'AnyPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class TestRF19APIKeyManagement(TestCase):
    """RF-19: Gestionar claves API personales"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='ValidPass123!',
        )
        self.client.force_login(self.user)

    def test_positive_api_keys_saved_and_persisted(self):
        response = self.client.post(reverse('profile'), {
            'email': 'test@example.com',
            'telefono': '',
            'google_api_key': 'AIza-google-key',
            'openai_api_key': 'sk-openai-key',
            'anthropic_api_key': 'sk-ant-key',
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.google_api_key, 'AIza-google-key')
        self.assertEqual(self.user.openai_api_key, 'sk-openai-key')
        self.assertEqual(self.user.anthropic_api_key, 'sk-ant-key')

    def test_negative_empty_key_accepted_system_uses_default(self):
        self.user.google_api_key = 'existing-key'
        self.user.save()
        response = self.client.post(reverse('profile'), {
            'email': 'test@example.com',
            'telefono': '',
            'google_api_key': '',
            'openai_api_key': '',
            'anthropic_api_key': '',
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.google_api_key)
        self.assertFalse(self.user.openai_api_key)

    def test_negative_profile_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse('profile'))
        self.assertRedirects(
            response, '/user/login/?next=/user/profile/',
            fetch_redirect_response=False,
        )
