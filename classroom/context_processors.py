"""Контекст бэкапа БД только на кастомных админках: /management/ и /files/management/."""

from classroom.db_backup_context import db_backup_banner_for_user


def db_backup_nav(request):
    path = getattr(request, "path", "") or ""
    if path.startswith("/files/management/") or path.startswith("/management/"):
        return db_backup_banner_for_user(request.user)
    return {}
