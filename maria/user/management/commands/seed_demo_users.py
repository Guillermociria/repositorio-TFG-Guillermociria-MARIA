from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

PASSWORD = 'demo123'

DEMO_USERS = [
    ('demo01', 'Ana García',       'ana.garcia@demo.com'),
    ('demo02', 'Carlos López',     'carlos.lopez@demo.com'),
    ('demo03', 'María Martínez',   'maria.martinez@demo.com'),
    ('demo04', 'Javier Sánchez',   'javier.sanchez@demo.com'),
    ('demo05', 'Laura González',   'laura.gonzalez@demo.com'),
    ('demo06', 'Pedro Rodríguez',  'pedro.rodriguez@demo.com'),
    ('demo07', 'Sofía Fernández',  'sofia.fernandez@demo.com'),
    ('demo08', 'Miguel Torres',    'miguel.torres@demo.com'),
    ('demo09', 'Elena Díaz',       'elena.diaz@demo.com'),
    ('demo10', 'David Ruiz',       'david.ruiz@demo.com'),
    ('demo11', 'Isabel Moreno',    'isabel.moreno@demo.com'),
    ('demo12', 'Antonio Jiménez',  'antonio.jimenez@demo.com'),
    ('demo13', 'Cristina Álvarez', 'cristina.alvarez@demo.com'),
    ('demo14', 'Francisco Romero', 'francisco.romero@demo.com'),
    ('demo15', 'Paula Navarro',    'paula.navarro@demo.com'),
    ('demo16', 'Alejandro Gil',    'alejandro.gil@demo.com'),
    ('demo17', 'Carmen Herrero',   'carmen.herrero@demo.com'),
    ('demo18', 'Rodrigo Molina',   'rodrigo.molina@demo.com'),
    ('demo19', 'Natalia Serrano',  'natalia.serrano@demo.com'),
    ('demo20', 'Hugo Blanco',      'hugo.blanco@demo.com'),
    ('demo21', 'Valeria Cano',     'valeria.cano@demo.com'),
    ('demo22', 'Marcos Vega',      'marcos.vega@demo.com'),
    ('demo23', 'Lucía Castro',     'lucia.castro@demo.com'),
    ('demo24', 'Adrián Ortega',    'adrian.ortega@demo.com'),
    ('demo25', 'Marta Delgado',    'marta.delgado@demo.com'),
    ('demo26', 'Daniel Ramos',     'daniel.ramos@demo.com'),
    ('demo27', 'Sara Vargas',      'sara.vargas@demo.com'),
    ('demo28', 'Rubén Santos',     'ruben.santos@demo.com'),
    ('demo29', 'Nuria Iglesias',   'nuria.iglesias@demo.com'),
    ('demo30', 'Alberto Reyes',    'alberto.reyes@demo.com'),
    ('demo31', 'Irene Muñoz',      'irene.munoz@demo.com'),
    ('demo32', 'Óscar Peña',       'oscar.pena@demo.com'),
    ('demo33', 'Lorena Flores',    'lorena.flores@demo.com'),
    ('demo34', 'Iván Cabrera',     'ivan.cabrera@demo.com'),
    ('demo35', 'Raquel Medina',    'raquel.medina@demo.com'),
]


class Command(BaseCommand):
    help = 'Crea 35 usuarios demo con contraseña demo123'

    def handle(self, *args, **kwargs):
        created_count = 0
        skipped_count = 0
        for username, full_name, email in DEMO_USERS:
            first, *rest = full_name.split(' ', 1)
            last = rest[0] if rest else ''
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email':      email,
                    'first_name': first,
                    'last_name':  last,
                },
            )
            if created:
                user.set_password(PASSWORD)
                user.save()
                created_count += 1
            else:
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'{created_count} usuarios creados, {skipped_count} ya existían. '
            f'Contraseña: {PASSWORD}'
        ))
