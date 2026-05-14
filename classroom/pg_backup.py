"""Утилиты pg_dump / pg_restore по настройкам Django DATABASES['default']."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from django.conf import settings


def is_postgresql() -> bool:
    engine = settings.DATABASES["default"].get("ENGINE", "")
    return engine == "django.db.backends.postgresql"


def is_sqlite() -> bool:
    engine = settings.DATABASES["default"].get("ENGINE", "")
    return engine.endswith("sqlite3")


def _pg_bin(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(
            f"Команда «{name}» не найдена в PATH. Установите клиент PostgreSQL "
            "той же мажорной версии, что и сервер (в Docker: postgresql-client-16 при postgres:16)."
        )
    return path


def _pg_env() -> dict[str, str]:
    db = settings.DATABASES["default"]
    env = os.environ.copy()
    password = db.get("PASSWORD")
    if password:
        env["PGPASSWORD"] = str(password)
    return env


def _pg_conn_args() -> list[str]:
    db = settings.DATABASES["default"]
    name = db.get("NAME") or ""
    user = db.get("USER") or ""
    host = db.get("HOST") or "localhost"
    port = str(db.get("PORT") or "5432")
    args = ["-h", host, "-p", port, "-U", user]
    if not str(name).strip():
        raise RuntimeError("В настройках БД не задано имя базы (NAME).")
    return args + [str(name)]


def run_pg_dump_custom_format(output_file: Path) -> None:
    """Снимок в формате custom (-Fc), подходит для pg_restore."""
    if not is_postgresql():
        raise RuntimeError("pg_dump доступен только при ENGINE=postgresql.")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _pg_bin("pg_dump"),
        "-Fc",
        "--no-owner",
        "-f",
        str(output_file),
        *_pg_conn_args(),
    ]
    proc = subprocess.run(
        cmd,
        env=_pg_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip() or f"код {proc.returncode}"
        raise RuntimeError(f"pg_dump завершился с ошибкой: {err}")


def run_pg_restore_custom_format(
    dump_file: Path,
    *,
    clean: bool = True,
) -> None:
    """Восстановление из архива custom (-Fc)."""
    if not is_postgresql():
        raise RuntimeError("pg_restore доступен только при ENGINE=postgresql.")
    if not dump_file.is_file():
        raise FileNotFoundError(str(dump_file))
    cmd = [
        _pg_bin("pg_restore"),
        "--verbose",
        "--no-owner",
        *_pg_conn_args(),
    ]
    if clean:
        cmd.extend(["--clean", "--if-exists"])
    cmd.append(str(dump_file))
    proc = subprocess.run(
        cmd,
        env=_pg_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip() or f"код {proc.returncode}"
        raise RuntimeError(f"pg_restore завершился с ошибкой: {err}")


def pg_dump_to_bytes() -> bytes:
    """Снимок БД в память (для скачивания из админ-панели)."""
    import tempfile

    from django.db import connections

    connections.close_all()
    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as tmp:
        path = Path(tmp.name)
    try:
        run_pg_dump_custom_format(path)
        return path.read_bytes()
    finally:
        path.unlink(missing_ok=True)


def pg_restore_from_uploaded_dump(uploaded_file, *, clean: bool = True) -> None:
    """
    Восстановление текущей БД из загруженного архива custom-формата (-Fc).
    Закрывает соединения Django перед pg_restore.
    """
    import tempfile

    from django.db import connections

    if not hasattr(uploaded_file, "chunks"):
        raise ValueError("Ожидался загруженный файл.")
    name = (getattr(uploaded_file, "name", "") or "").lower()
    if not name.endswith(".dump"):
        raise ValueError("Файл должен иметь расширение .dump (формат pg_dump -Fc).")

    connections.close_all()
    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as tmp:
        path = Path(tmp.name)
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
    try:
        run_pg_restore_custom_format(path, clean=clean)
    finally:
        path.unlink(missing_ok=True)
