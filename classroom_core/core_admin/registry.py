"""Регистрация моделей и параметров списков для панели управления."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

from django.db import models

from classroom_core import models as cc_models


@dataclass
class PanelModelConfig:
    """Настройки отображения модели в панели управления."""

    model: type[models.Model]
    list_display: tuple[str, ...]
    search_fields: tuple[str, ...]
    list_filter: tuple[str, ...]
    ordering: tuple[str, ...] = ("-pk",)


def _iter_cc_models() -> list[type[models.Model]]:
    out: list[type[models.Model]] = []
    for _name, obj in inspect.getmembers(cc_models, inspect.isclass):
        if not issubclass(obj, models.Model) or obj._meta.abstract:
            continue
        if getattr(obj._meta, "app_label", None) != "classroom_core":
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
    "course": {
        "list_display": (
            "id",
            "title",
            "code",
            "status",
            "instructor",
            "start_date",
            "end_date",
        ),
        "search_fields": ("title", "description", "short_description", "code"),
        "list_filter": ("status", "is_public", "instructor"),
    },
    "userprofile": {
        "list_display": ("id", "user", "role", "department", "student_group", "access_class"),
        "search_fields": ("department", "position", "phone", "user__username", "user__email", "user__first_name", "user__last_name"),
        "list_filter": ("role", "access_class", "student_group"),
    },
}


def build_registry() -> dict[str, PanelModelConfig]:
    registry: dict[str, PanelModelConfig] = {}
    for model in _iter_cc_models():
        key = model._meta.model_name
        over = _OVERRIDES.get(key, {})
        registry[key] = PanelModelConfig(
            model=model,
            list_display=tuple(over.get("list_display", _default_list_display(model))),
            search_fields=tuple(over.get("search_fields", _default_search_fields(model))),
            list_filter=tuple(over.get("list_filter", _default_list_filter(model))),
            ordering=tuple(over.get("ordering", _default_ordering(model))),
        )
    return registry


CORE_ADMIN_REGISTRY: dict[str, PanelModelConfig] = build_registry()


def get_config(model_name: str) -> PanelModelConfig | None:
    return CORE_ADMIN_REGISTRY.get(model_name)
