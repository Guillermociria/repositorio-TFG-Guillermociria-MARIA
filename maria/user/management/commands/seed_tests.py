from django.core.management.base import BaseCommand
from user.models import User


TEST_USERS = [
    {'username': 'test_perf',  'email': 'perf@test.com', 'password': 'PerfPass123!'},
    {'username': 'pw_test',    'email': 'pw@test.com',   'password': 'PwPass123!'},
]


class Command(BaseCommand):
    help = 'Crea los usuarios necesarios para tests de Locust y Playwright'

    def handle(self, *args, **options):
        for u in TEST_USERS:
            obj, created = User.objects.get_or_create(
                username=u['username'],
                defaults={'email': u['email']},
            )
            if created:
                obj.set_password(u['password'])
                obj.save()
                self.stdout.write(self.style.SUCCESS(f"Creado: {u['username']}"))
            else:
                self.stdout.write(f"Ya existe: {u['username']}")
