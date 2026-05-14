from pathlib import Path

from django.core.management import BaseCommand
from django.db import connections

from classroom.pg_backup import is_postgresql, run_pg_restore_custom_format


class Command(BaseCommand):
    help = "Импорт базы из файла pg_dump custom (-Fc), например db.dump"

    def add_arguments(self, parser):
        parser.add_argument("dump_file", type=str, help="Путь к файлу .dump (формат custom)")
        parser.add_argument(
            "--no-clean",
            action="store_true",
            help="Не использовать --clean/--if-exists у pg_restore",
        )

    def handle(self, *args, **options):
        if not is_postgresql():
            self.stderr.write(self.style.ERROR("Только для ENGINE=django.db.backends.postgresql"))
            return
        path = Path(options["dump_file"]).resolve()
        if not path.is_file():
            self.stderr.write(self.style.ERROR(f"Файл не найден: {path}"))
            return
        connections.close_all()
        run_pg_restore_custom_format(path, clean=not options["no_clean"])
        self.stdout.write(self.style.SUCCESS(f"Импорт завершён: {path}"))
