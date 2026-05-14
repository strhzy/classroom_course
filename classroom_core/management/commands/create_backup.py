import json
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, CommandError

from classroom.pg_backup import is_postgresql, run_pg_dump_custom_format


class Command(BaseCommand):
    help = "Создать резервную копию (PostgreSQL: db.dump + media в zip)"

    def add_arguments(self, parser):
        parser.add_argument("--output-dir", default=str(Path(settings.BASE_DIR) / "backups"))
        parser.add_argument("--keep-last", type=int, default=7)

    def handle(self, *args, **options):
        if not is_postgresql():
            raise CommandError(
                "Резервная копия поддерживается только при подключении к PostgreSQL "
                "(DJANGO_USE_SQLITE не включён и ENGINE=postgresql)."
            )

        output_dir = Path(options["output_dir"])
        keep_last = options["keep_last"]
        output_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_dir = output_dir / f"snapshot_{ts}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        db_path = snapshot_dir / "db.dump"
        run_pg_dump_custom_format(db_path)
        db_backend = "postgresql"
        db_dump_size = db_path.stat().st_size if db_path.exists() else 0

        media_root = Path(settings.MEDIA_ROOT)
        media_target = snapshot_dir / "media"
        if media_root.exists():
            shutil.copytree(media_root, media_target)
        else:
            media_target.mkdir(parents=True, exist_ok=True)

        media_files = [p for p in media_target.rglob("*") if p.is_file()]
        manifest = {
            "timestamp": ts,
            "db_backend": db_backend,
            "db_dump_file": db_path.name,
            "media_files_count": len(media_files),
            "media_files": [str(p.relative_to(media_target)) for p in media_files],
            "db_dump_size": db_dump_size,
        }
        (snapshot_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        archive_path = shutil.make_archive(str(snapshot_dir), "zip", root_dir=snapshot_dir)
        shutil.rmtree(snapshot_dir, ignore_errors=True)

        archives = sorted(output_dir.glob("snapshot_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in archives[keep_last:]:
            old.unlink(missing_ok=True)

        self.stdout.write(self.style.SUCCESS(f"Backup created: {archive_path}"))
