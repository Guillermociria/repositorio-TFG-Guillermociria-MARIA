from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

DEMO_USER = {
    'username': 'demo',
    'email':    'demo@example.com',
    'password': 'demo1234',
}


class Command(BaseCommand):
    help = 'Crea un usuario de prueba (demo/demo1234)'

    def handle(self, *args, **kwargs):
        user, created = User.objects.get_or_create(
            username=DEMO_USER['username'],
            defaults={'email': DEMO_USER['email']},
        )
        if created:
            user.set_password(DEMO_USER['password'])
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f"Usuario creado: {DEMO_USER['username']} / {DEMO_USER['password']}"
            ))
        else:
            self.stdout.write(f"Usuario '{DEMO_USER['username']}' ya existe.")
