import json
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.db import connections

from classroom.pg_backup import is_postgresql, run_pg_restore_custom_format


class Command(BaseCommand):
    help = "Restore application backup (database + media) from archive"

    def add_arguments(self, parser):
        parser.add_argument("archive", help="Path to backup archive .zip")
        parser.add_argument("--flush", action="store_true", help="Flush DB before restore (только для JSON)")
        parser.add_argument(
            "--no-pg-clean",
            action="store_true",
            help="Не передавать pg_restore --clean (осторожно: возможны конфликты объектов)",
        )

    def handle(self, *args, **options):
        archive_path = Path(options["archive"]).resolve()
        if not archive_path.exists():
            self.stderr.write(self.style.ERROR(f"Archive not found: {archive_path}"))
            return

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            shutil.unpack_archive(str(archive_path), str(tmp_dir))

            manifest_path = tmp_dir / "manifest.json"
            manifest = {}
            if manifest_path.is_file():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    manifest = {}

            db_dump = tmp_dir / "db.dump"
            db_json = tmp_dir / "db.json"
            media_dir = tmp_dir / "media"

            db_backend = manifest.get("db_backend")
            restored_from_json = False
            if db_dump.is_file():
                if not is_postgresql():
                    self.stderr.write(
                        self.style.ERROR(
                            "В архиве дамп PostgreSQL (db.dump), а текущий ENGINE БД не postgresql. "
                            "Переключите DATABASE на PostgreSQL или восстановите в подходящей среде."
                        )
                    )
                    return
                connections.close_all()
                run_pg_restore_custom_format(db_dump, clean=not options["no_pg_clean"])
            elif db_json.is_file():
                restored_from_json = True
                if options["flush"]:
                    call_command("flush", interactive=False)
                call_command("loaddata", str(db_json))
            else:
                self.stderr.write(self.style.ERROR("В архиве не найден ни db.dump, ни db.json"))
                return

            if restored_from_json and db_backend == "postgresql":
                self.stdout.write(
                    self.style.WARNING(
                        "В архиве только JSON, тогда как основная БД — PostgreSQL. "
                        "Для полного снимка используйте архивы с db.dump (create_backup на Postgres)."
                    )
                )

            media_root = Path(settings.MEDIA_ROOT)
            media_root.mkdir(parents=True, exist_ok=True)
            if media_dir.exists():
                shutil.copytree(media_dir, media_root, dirs_exist_ok=True)

        self.stdout.write(self.style.SUCCESS("Backup restored successfully"))
