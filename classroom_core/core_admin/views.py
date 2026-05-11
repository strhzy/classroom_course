"""Представления панели управления: списки, формы, резервные копии."""

from __future__ import annotations

import shutil
import tempfile
from io import StringIO
from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldDoesNotExist, PermissionDenied, ValidationError
from django.core.management import call_command
from django.core.paginator import Paginator
from django.db import connections, models
from django.db.models import Q
from django.forms.models import modelform_factory
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from classroom_core.core_admin.registry import CORE_ADMIN_REGISTRY, get_config


def _can_core_admin(user) -> bool:
    if not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    profile = getattr(user, "profile", None)
    if profile is None:
        return False
    return bool(profile.is_admin() or profile.is_staff())


def _require_core_admin(user):
    if not _can_core_admin(user):
        raise PermissionDenied


def _widgets_for_model(model: type[models.Model]) -> dict[str, forms.Widget]:
    widgets: dict[str, forms.Widget] = {}
    for f in model._meta.fields:
        base = {"class": "form-control"}
        if isinstance(f, models.BooleanField):
            widgets[f.name] = forms.CheckboxInput(attrs={"class": "form-check-input"})
        elif isinstance(f, models.DateTimeField):
            widgets[f.name] = forms.DateTimeInput(attrs={**base, "type": "datetime-local"})
        elif isinstance(f, models.DateField):
            widgets[f.name] = forms.DateInput(attrs={**base, "type": "date"})
        elif isinstance(f, models.TimeField):
            widgets[f.name] = forms.TimeInput(attrs={**base, "type": "time"})
        elif isinstance(f, models.URLField):
            widgets[f.name] = forms.URLInput(attrs=base)
        elif isinstance(f, models.EmailField):
            widgets[f.name] = forms.EmailInput(attrs=base)
        elif isinstance(f, models.TextField):
            row_height = min(10, max(3, (getattr(f, "max_length", 120) or 120) // 40))
            widgets[f.name] = forms.Textarea(attrs={**base, "rows": row_height})
        elif isinstance(f, (models.ForeignKey, models.OneToOneField)):
            widgets[f.name] = forms.Select(attrs={"class": "form-select"})
        elif getattr(f, "choices", None):
            widgets[f.name] = forms.Select(attrs={"class": "form-select"})
        elif isinstance(
            f,
            (
                models.IntegerField,
                models.BigIntegerField,
                models.PositiveIntegerField,
                models.PositiveSmallIntegerField,
            ),
        ):
            widgets[f.name] = forms.NumberInput(attrs=base)
        elif isinstance(f, (models.DecimalField, models.FloatField)):
            widgets[f.name] = forms.NumberInput(attrs={**base, "step": "any"})
        elif isinstance(f, (models.FileField, models.ImageField)):
            widgets[f.name] = forms.ClearableFileInput(attrs={"class": "form-control"})
        elif isinstance(f, models.JSONField):
            widgets[f.name] = forms.Textarea(attrs={**base, "rows": 6, "style": "font-family: monospace;"})
        else:
            widgets[f.name] = forms.TextInput(attrs=base)

    for f in model._meta.many_to_many:
        widgets[f.name] = forms.SelectMultiple(attrs={"class": "form-select", "size": "8"})
    return widgets


def _make_model_form(model: type[models.Model]):
    return modelform_factory(
        model,
        fields="__all__",
        widgets=_widgets_for_model(model),
    )


def _parse_bool_param(raw: str | None) -> bool | None:
    if raw is None or raw == "":
        return None
    if raw in ("1", "true", "True", "yes", "on"):
        return True
    if raw in ("0", "false", "False", "no", "off"):
        return False
    return None


def _apply_search(qs, model: type[models.Model], q: str, search_fields: tuple[str, ...]):
    if not q or not search_fields:
        return qs
    q_clean = q.strip()
    if not q_clean:
        return qs
    expr = Q()
    for name in search_fields:
        try:
            model._meta.get_field(name.split("__")[0])
        except FieldDoesNotExist:
            continue
        expr |= Q(**{f"{name}__icontains": q_clean})
    return qs.filter(expr)


def _apply_filters(request, qs, config):
    model = config.model
    for fname in config.list_filter:
        key = f"f_{fname}"
        raw = request.GET.get(key)
        if raw in (None, ""):
            continue
        try:
            field = model._meta.get_field(fname)
        except FieldDoesNotExist:
            continue
        if isinstance(field, (models.BooleanField, models.NullBooleanField)):
            b = _parse_bool_param(raw)
            if b is not None:
                qs = qs.filter(**{fname: b})
        elif isinstance(field, (models.ForeignKey, models.OneToOneField)):
            try:
                qs = qs.filter(**{field.attname: int(raw)})
            except (TypeError, ValueError):
                continue
        else:
            qs = qs.filter(**{fname: raw})
    return qs


def _ordering(model: type[models.Model], config, request):
    order_fields = request.GET.getlist("o") or list(config.ordering)
    valid_names = {f.name for f in model._meta.fields}
    cleaned: list[str] = []
    for item in order_fields:
        if not item:
            continue
        desc = item.startswith("-")
        name = item[1:] if desc else item
        if name not in valid_names:
            continue
        cleaned.append(f"-{name}" if desc else name)
    if not cleaned:
        cleaned = list(config.ordering)
    return cleaned


def _cell_display(obj, field_name: str):
    try:
        val = getattr(obj, field_name)
        if callable(val):
            val = val()
    except Exception:
        return "—"
    if val is None or val == "":
        return "—"
    return str(val)


@login_required
def core_admin_index(request):
    _require_core_admin(request.user)
    apps_models = []
    for name, cfg in sorted(CORE_ADMIN_REGISTRY.items(), key=lambda x: x[1].model._meta.verbose_name_plural.lower()):
        model = cfg.model
        count = model.objects.count()
        apps_models.append(
            {
                "key": name,
                "verbose_name": model._meta.verbose_name_plural,
                "count": count,
                "changelist_url": reverse("classroom_core:core_admin_changelist", kwargs={"model_name": name}),
            }
        )
    db_engine = settings.DATABASES["default"]["ENGINE"]
    return render(
        request,
        "classroom_core/core_admin/index.html",
        {
            "apps_models": apps_models,
            "is_sqlite": db_engine.endswith("sqlite3"),
        },
    )


@login_required
def core_admin_changelist(request, model_name: str):
    _require_core_admin(request.user)
    config = get_config(model_name)
    if not config:
        raise Http404
    model = config.model
    qs = model.objects.all()
    q = request.GET.get("q", "")
    qs = _apply_search(qs, model, q, config.search_fields)
    qs = _apply_filters(request, qs, config)
    ordering = _ordering(model, config, request)
    qs = qs.order_by(*ordering)

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    filter_choices = []
    for fname in config.list_filter:
        try:
            field = model._meta.get_field(fname)
        except FieldDoesNotExist:
            continue
        param = f"f_{fname}"
        current = request.GET.get(param)
        choices = []
        if isinstance(field, (models.ForeignKey, models.OneToOneField)):
            rel_model = field.related_model
            for robj in rel_model.objects.order_by("pk")[:500]:
                choices.append({"value": str(robj.pk), "label": str(robj)})
        elif getattr(field, "choices", None):
            for value, label in field.choices:
                choices.append({"value": str(value), "label": str(label)})
        elif isinstance(field, (models.BooleanField, models.NullBooleanField)):
            choices = [
                {"value": "true", "label": "Да"},
                {"value": "false", "label": "Нет"},
            ]
        filter_choices.append(
            {
                "field": fname,
                "param": param,
                "label": field.verbose_name,
                "choices": choices,
                "current": current or "",
            }
        )

    rows = []
    for obj in page_obj:
        rows.append({"obj": obj, "cells": [_cell_display(obj, col) for col in config.list_display]})

    context = {
        "config": config,
        "model_name": model_name,
        "verbose_name_plural": model._meta.verbose_name_plural,
        "page_obj": page_obj,
        "q": q,
        "list_display": config.list_display,
        "filter_choices": filter_choices,
        "ordering": ordering,
        "rows": rows,
        "add_url": reverse("classroom_core:core_admin_add", kwargs={"model_name": model_name}),
    }
    return render(request, "classroom_core/core_admin/changelist.html", context)


@login_required
@require_http_methods(["POST"])
def core_admin_bulk_delete(request, model_name: str):
    _require_core_admin(request.user)
    config = get_config(model_name)
    if not config:
        raise Http404
    model = config.model
    ids = request.POST.getlist("_selected_action")
    if not ids:
        messages.warning(request, "Не выбраны объекты для удаления.")
        return redirect("classroom_core:core_admin_changelist", model_name=model_name)
    deleted = 0
    for sid in ids:
        try:
            pk = int(sid)
        except (TypeError, ValueError):
            continue
        obj = model.objects.filter(pk=pk).first()
        if obj:
            obj.delete()
            deleted += 1
    messages.success(request, f"Удалено объектов: {deleted}")
    return redirect("classroom_core:core_admin_changelist", model_name=model_name)


@login_required
def core_admin_add(request, model_name: str):
    _require_core_admin(request.user)
    config = get_config(model_name)
    if not config:
        raise Http404
    model = config.model
    FormClass = _make_model_form(model)
    if request.method == "POST":
        form = FormClass(request.POST, request.FILES)
        if form.is_valid():
            try:
                obj = form.save()
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, f"Объект «{obj}» создан.")
                return redirect(
                    "classroom_core:core_admin_change",
                    model_name=model_name,
                    object_id=obj.pk,
                )
    else:
        form = FormClass()
    return render(
        request,
        "classroom_core/core_admin/change_form.html",
        {
            "config": config,
            "model_name": model_name,
            "verbose_name": model._meta.verbose_name,
            "model_verbose_name_plural": model._meta.verbose_name_plural,
            "form": form,
            "object": None,
            "is_add": True,
            "changelist_url": reverse("classroom_core:core_admin_changelist", kwargs={"model_name": model_name}),
        },
    )


@login_required
def core_admin_change(request, model_name: str, object_id: int):
    _require_core_admin(request.user)
    config = get_config(model_name)
    if not config:
        raise Http404
    model = config.model
    obj = get_object_or_404(model, pk=object_id)
    FormClass = _make_model_form(model)
    if request.method == "POST":
        form = FormClass(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            try:
                form.save()
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, "Изменения сохранены.")
                return redirect(
                    "classroom_core:core_admin_change",
                    model_name=model_name,
                    object_id=object_id,
                )
    else:
        form = FormClass(instance=obj)
    return render(
        request,
        "classroom_core/core_admin/change_form.html",
        {
            "config": config,
            "model_name": model_name,
            "verbose_name": model._meta.verbose_name,
            "model_verbose_name_plural": model._meta.verbose_name_plural,
            "form": form,
            "object": obj,
            "is_add": False,
            "changelist_url": reverse("classroom_core:core_admin_changelist", kwargs={"model_name": model_name}),
            "delete_url": reverse(
                "classroom_core:core_admin_delete",
                kwargs={"model_name": model_name, "object_id": object_id},
            ),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def core_admin_delete(request, model_name: str, object_id: int):
    _require_core_admin(request.user)
    config = get_config(model_name)
    if not config:
        raise Http404
    model = config.model
    obj = get_object_or_404(model, pk=object_id)
    if request.method == "POST":
        label = str(obj)
        obj.delete()
        messages.success(request, f"Удалено: {label}")
        return redirect("classroom_core:core_admin_changelist", model_name=model_name)
    return render(
        request,
        "classroom_core/core_admin/delete_confirmation.html",
        {
            "config": config,
            "model_name": model_name,
            "object": obj,
            "verbose_name": model._meta.verbose_name,
            "model_verbose_name_plural": model._meta.verbose_name_plural,
            "changelist_url": reverse("classroom_core:core_admin_changelist", kwargs={"model_name": model_name}),
        },
    )


@login_required
def core_admin_backup_download(request):
    """Выгрузка данных в JSON (без таблицы сессий)."""
    _require_core_admin(request.user)
    buf = StringIO()
    call_command(
        "dumpdata",
        exclude=["sessions.Session"],
        natural_foreign=True,
        indent=2,
        stdout=buf,
    )
    data = buf.getvalue().encode("utf-8")
    filename = f"backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
    response = HttpResponse(data, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def core_admin_backup_sqlite_download(request):
    """Скачать файл SQLite (только для sqlite3)."""
    _require_core_admin(request.user)
    engine = settings.DATABASES["default"]["ENGINE"]
    if not engine.endswith("sqlite3"):
        raise Http404
    db_path = Path(settings.DATABASES["default"]["NAME"])
    if not db_path.is_file():
        raise Http404

    connections.close_all()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite3") as tmp:
        tmp_path = Path(tmp.name)
    try:
        shutil.copy2(db_path, tmp_path)
        data = tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)

    filename = f"db_{timezone.now().strftime('%Y%m%d_%H%M%S')}.sqlite3"
    response = HttpResponse(data, content_type="application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
