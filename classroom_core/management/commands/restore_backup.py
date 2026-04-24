import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Restore application backup (database + media) from archive"

    def add_arguments(self, parser):
        parser.add_argument("archive", help="Path to backup archive .zip")
        parser.add_argument("--flush", action="store_true", help="Flush DB before restore")

    def handle(self, *args, **options):
        archive_path = Path(options["archive"]).resolve()
        if not archive_path.exists():
            self.stderr.write(self.style.ERROR(f"Archive not found: {archive_path}"))
            return

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            shutil.unpack_archive(str(archive_path), str(tmp_dir))

            db_dump = tmp_dir / "db.json"
            media_dir = tmp_dir / "media"
            if not db_dump.exists():
                self.stderr.write(self.style.ERROR("db.json not found in archive"))
                return

            if options["flush"]:
                call_command("flush", interactive=False)

            call_command("loaddata", str(db_dump))

            media_root = Path(settings.MEDIA_ROOT)
            media_root.mkdir(parents=True, exist_ok=True)
            if media_dir.exists():
                shutil.copytree(media_dir, media_root, dirs_exist_ok=True)

        self.stdout.write(self.style.SUCCESS("Backup restored successfully"))
