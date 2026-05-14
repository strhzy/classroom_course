"""Контекст для панелей: блок резервного копирования (создание/восстановление .dump при PostgreSQL)."""

from __future__ import annotations

from typing import Any


def db_backup_banner_for_user(user) -> dict[str, Any]:
    """
    Те же права, что в core_admin: superuser или профиль admin/staff.
    Блок показывается всегда на кастомных админках; активные кнопки — только при ENGINE=postgresql.
    """
    from django.urls import reverse

    from classroom.pg_backup import is_postgresql

    empty: dict[str, Any] = {"show_db_backup": False}
    if not getattr(user, "is_authenticated", False):
        return empty
    profile = getattr(user, "profile", None)
    can = getattr(user, "is_superuser", False) or (
        profile is not None and bool(profile.is_admin() or profile.is_staff())
    )
    if not can:
        return empty
    pg = is_postgresql()
    return {
        "show_db_backup": True,
        "db_backup_postgres_available": pg,
        "db_backup_pg_url": reverse("classroom_core:core_admin_backup_postgres"),
        "db_backup_pg_restore_url": reverse("classroom_core:core_admin_backup_postgres_restore"),
    }

