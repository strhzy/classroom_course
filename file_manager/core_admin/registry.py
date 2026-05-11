"""Регистрация моделей для панели управления file_manager."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

from django.contrib.auth.models import User
from django.db import models

from file_manager import models as fm_models


@dataclass
class PanelModelConfig:
    """Настройки отображения модели в панели управления."""

    model: type[models.Model]
    list_display: tuple[str, ...]
    search_fields: tuple[str, ...]
    list_filter: tuple[str, ...]
    ordering: tuple[str, ...] = ("-pk",)
    section_label: str | None = None
    allow_add: bool = True


def _iter_fm_models() -> list[type[models.Model]]:
    out: list[type[models.Model]] = []
    for _name, obj in inspect.getmembers(fm_models, inspect.isclass):
        if not issubclass(obj, models.Model) or obj._meta.abstract:
            continue
        if getattr(obj._meta, "app_label", None) != "file_manager":
            continue
        if obj is models.Model:
            continue
        out.append(obj)
    return sorted(out, key=lambda m: m._meta.verbose_name_plural.lower())


def _is_searchable(f: models.Field) -> bool:
    return isinstance(
        f,
        (models.CharField, models.TextField, models.GenericIPAddressField, models.UUIDField),
    )


def _default_list_display(model: type[models.Model]) -> tuple[str, ...]:
    names: list[str] = []
    for f in model._meta.fields:
        if len(names) >= 5:
            break
        if f.name in ("password",):
            continue
        names.append(f.name)
    if not names:
        names = ["id"]
    return tuple(names)


def _default_search_fields(model: type[models.Model]) -> tuple[str, ...]:
    names: list[str] = []
    for f in model._meta.fields:
        if _is_searchable(f) and len(names) < 8:
            names.append(f.name)
    return tuple(names)


def _default_list_filter(model: type[models.Model]) -> tuple[str, ...]:
    names: list[str] = []
    for f in model._meta.fields:
        if len(names) >= 10:
            break
        if isinstance(f, (models.BooleanField, models.NullBooleanField)):
            names.append(f.name)
        elif bool(getattr(f, "choices", None)):
            names.append(f.name)
        elif isinstance(f, (models.ForeignKey, models.OneToOneField)):
            names.append(f.name)
    return tuple(names)


def _default_ordering(model: type[models.Model]) -> tuple[str, ...]:
    ordering = getattr(model._meta, "ordering", None) or ()
    if ordering:
        return tuple(ordering)
    return ("-id",)


_OVERRIDES: dict[str, dict[str, Any]] = {
    "file": {
        "list_display": (
            "id",
            "title",
            "uploaded_by",
            "storage_provider",
            "file_type",
            "file_size",
            "uploaded_at",
        ),
        "search_fields": (
            "title",
            "description",
            "uploaded_by__username",
            "uploaded_by__email",
            "yandex_path",
        ),
        "list_filter": ("storage_provider", "file_type", "visibility", "importance"),
        "ordering": ("-uploaded_at",),
    },
    "tag": {
        "list_display": ("id", "name", "color"),
        "search_fields": ("name",),
        "list_filter": (),
        "ordering": ("name",),
    },
    "filecomment": {
        "list_display": ("id", "file", "author", "created_at"),
        "search_fields": ("content", "file__title", "author__username"),
        "list_filter": ("created_at",),
        "ordering": ("-created_at",),
    },
    "fileversion": {
        "list_display": ("id", "file", "version_number", "changed_by", "created_at"),
        "search_fields": ("change_description", "file__title", "snapshot_title"),
        "list_filter": ("created_at",),
        "ordering": ("-version_number",),
    },
    "fileactivity": {
        "list_display": ("id", "user", "activity_type", "file", "created_at"),
        "search_fields": ("description", "file__title", "user__username"),
        "list_filter": ("activity_type", "created_at"),
        "ordering": ("-created_at",),
    },
    "userstoragequota": {
        "list_display": ("id", "user", "total_quota_bytes", "used_bytes", "last_updated"),
        "search_fields": ("user__username", "user__email"),
        "list_filter": (),
        "ordering": ("-last_updated",),
        "section_label": "Квоты хранилища",
    },
    "externalstorageconnection": {
        "list_display": ("id", "user", "provider", "expires_at", "updated_at"),
        "search_fields": ("user__username", "user__email"),
        "list_filter": ("provider",),
        "ordering": ("-updated_at",),
    },
    "favoritecollection": {
        "list_display": ("id", "user", "title", "created_at"),
        "search_fields": ("title", "user__username"),
        "list_filter": (),
        "ordering": ("title",),
    },
    "favoritecollectionitem": {
        "list_display": ("id", "collection", "file", "created_at"),
        "search_fields": ("collection__title", "file__title"),
        "list_filter": (),
        "ordering": ("-created_at",),
    },
    "sharedworkspace": {
        "list_display": ("id", "title", "owner", "created_at"),
        "search_fields": ("title", "owner__username"),
        "list_filter": (),
        "ordering": ("-created_at",),
    },
}


def build_registry() -> dict[str, PanelModelConfig]:
    registry: dict[str, PanelModelConfig] = {}
    for model in _iter_fm_models():
        key = model._meta.model_name
        over = _OVERRIDES.get(key, {})
        registry[key] = PanelModelConfig(
            model=model,
            list_display=tuple(over.get("list_display", _default_list_display(model))),
            search_fields=tuple(over.get("search_fields", _default_search_fields(model))),
            list_filter=tuple(over.get("list_filter", _default_list_filter(model))),
            ordering=tuple(over.get("ordering", _default_ordering(model))),
            section_label=over.get("section_label"),
            allow_add=over.get("allow_add", True),
        )

    registry["django_user"] = PanelModelConfig(
        model=User,
        list_display=(
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
        ),
        search_fields=("username", "email", "first_name", "last_name"),
        list_filter=("is_active", "is_staff", "is_superuser"),
        ordering=("-date_joined",),
        section_label="Пользователи",
        allow_add=True,
    )
    return registry


FM_ADMIN_REGISTRY: dict[str, PanelModelConfig] = build_registry()


def get_config(model_name: str) -> PanelModelConfig | None:
    return FM_ADMIN_REGISTRY.get(model_name)


def display_label(config: PanelModelConfig) -> str:
    if config.section_label:
        return config.section_label
    return config.model._meta.verbose_name_plural
