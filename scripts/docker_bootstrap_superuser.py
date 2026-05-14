"""Первый запуск Docker: суперпользователь admin / admin (см. entrypoint.sh)."""

import os
import sys
from pathlib import Path

# При запуске как `python scripts/...py` в sys.path попадает только scripts/ — нужен корень проекта.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "classroom.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

# Только для пустой БД / первого деплоя. В продакшене смените пароль сразу после входа.
_BOOTSTRAP_USERNAME = "admin"
_BOOTSTRAP_PASSWORD = "admin"
_BOOTSTRAP_EMAIL = "admin@localhost"


def main() -> None:
    User = get_user_model()
    if User.objects.filter(is_superuser=True).exists():
        print("Суперпользователи уже есть — автосоздание admin/admin пропущено.")
        return

    existing = User.objects.filter(username=_BOOTSTRAP_USERNAME).first()
    if existing:
        existing.is_superuser = True
        existing.is_staff = True
        existing.is_active = True
        existing.set_password(_BOOTSTRAP_PASSWORD)
        existing.save()
        print(
            f"Учётная запись «{_BOOTSTRAP_USERNAME}» получила права суперпользователя; "
            f"пароль установлен: {_BOOTSTRAP_PASSWORD}"
        )
        return

    User.objects.create_superuser(
        _BOOTSTRAP_USERNAME,
        _BOOTSTRAP_EMAIL,
        _BOOTSTRAP_PASSWORD,
    )
    print(
        f"Создан суперпользователь: {_BOOTSTRAP_USERNAME} / {_BOOTSTRAP_PASSWORD} "
        "(смените пароль после первого входа.)"
    )


if __name__ == "__main__":
    main()
