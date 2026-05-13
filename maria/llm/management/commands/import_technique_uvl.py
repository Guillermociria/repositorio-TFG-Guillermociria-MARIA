import os
from django.core.management.base import BaseCommand, CommandError
from llm.models import Technique
from llm.uvl_parser import parse_technique_uvl, UVLParseError


class Command(BaseCommand):
    help = 'Importa técnicas desde ficheros .uvl'

    def add_arguments(self, parser):
        parser.add_argument('uvl_files', nargs='+', type=str,
                            help='Ruta(s) a ficheros .uvl')
        parser.add_argument('--update', action='store_true',
                            help='Actualizar técnica si ya existe (update_or_create)')

    def handle(self, *args, **options):
        ok = errors = skipped = 0
        for path in options['uvl_files']:
            if not os.path.exists(path):
                self.stderr.write(self.style.ERROR(f"No encontrado: {path}"))
                errors += 1
                continue

            try:
                with open(path, encoding='utf-8') as f:
                    data = parse_technique_uvl(f.read())
            except UVLParseError as e:
                self.stderr.write(self.style.ERROR(f"[{path}] Parse error: {e}"))
                errors += 1
                continue

            tech_id = data.pop('tech_id') if 'tech_id' in data else data.get('tech_id')
            # restore for create
            data_full = {'tech_id': tech_id, **data}

            if options['update']:
                _, created = Technique.objects.update_or_create(
                    tech_id=tech_id, defaults=data
                )
                verb = 'Creada' if created else 'Actualizada'
                ok += 1
            else:
                if Technique.objects.filter(tech_id=tech_id).exists():
                    self.stdout.write(self.style.WARNING(
                        f"[{path}] '{tech_id}' ya existe — usa --update para sobreescribir."
                    ))
                    skipped += 1
                    continue
                Technique.objects.create(**data_full)
                verb = 'Creada'
                ok += 1

            obj = Technique.objects.get(tech_id=tech_id)
            self.stdout.write(self.style.SUCCESS(f"{verb}: {obj.icon} {obj.name} ({tech_id})"))

        self.stdout.write(f"\n{ok} importadas, {skipped} omitidas, {errors} errores.")
