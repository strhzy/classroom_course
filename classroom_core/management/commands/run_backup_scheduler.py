import time
from datetime import datetime

from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Run backup scheduler at 00:00 and 12:00"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Backup scheduler started"))
        last_run_key = None
        while True:
            now = datetime.now()
            if now.hour in (0, 12) and now.minute == 0:
                run_key = f"{now.date()}-{now.hour}"
                if run_key != last_run_key:
                    call_command("create_backup")
                    last_run_key = run_key
            time.sleep(30)
