"""Панель управления file_manager: списки, формы, бэкапы, учётные записи Django."""

from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal
from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import FieldDoesNotExist, PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.forms.models import modelform_factory
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods


from file_manager.core_admin.registry import (
    FM_ADMIN_REGISTRY,
    PanelModelConfig,
    display_label,
    get_config,
)
from file_manager.models import (
    ExternalStorageConnection,
    File,
    UserStorageQuota,
)
from file_manager.quota_units import (
    UNIT_LABELS_CHOICES,
    bytes_to_amount_unit,
    format_bytes_ru,
    parse_quota_to_bytes,
)


def _can_fm_admin(user) -> bool:
    if not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    profile = getattr(user, "profile", None)
    if profile is None:
        return False
    return bool(profile.is_admin() or profile.is_staff())


def _require_fm_admin(user):
    if not _can_fm_admin(user):
        raise PermissionDenied


def _can_manage_django_users(user) -> bool:
    return user.is_authenticated and (
        getattr(user, "is_superuser", False) or getattr(user, "is_staff", False)
    )


def _require_django_user_admin(user):
    if not _can_manage_django_users(user):
        raise PermissionDenied


def _local_file_quota_editable() -> bool:
    """Лимит квоты настраивается для локального хранилища (по умолчанию)."""
    s = getattr(settings, "DEFAULT_FILE_STORAGE", "") or ""
    return "FileSystemStorage" in s or s.endswith(".FileSystemStorage") or s == ""


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


class DjangoUserPanelForm(forms.ModelForm):
    """Учётная запись Django в панели: поля профиля + назначение пароля (создание / смена)."""

    new_password1 = forms.CharField(
        label="Пароль",
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
        help_text="",
    )
    new_password2 = forms.CharField(
        label="Пароль (ещё раз)",
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
        help_text="",
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
        )
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_superuser": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["new_password1"].required = False
            self.fields["new_password2"].required = False
            self.fields["new_password1"].help_text = (
                "Оставьте оба поля пустыми, чтобы не менять пароль. "
                "Иначе введите новый пароль дважды."
            )
            self.fields["new_password2"].help_text = ""
        else:
            self.fields["new_password1"].required = True
            self.fields["new_password2"].required = True
            self.fields["new_password1"].help_text = (
                "Начальный пароль для входа по логину и паролю (не хранится в открытом виде)."
            )
            self.fields["new_password2"].help_text = "Повторите пароль."
        order = (
            "username",
            "new_password1",
            "new_password2",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
        )
        new_fields = OrderedDict()
        for name in order:
            if name in self.fields:
                new_fields[name] = self.fields[name]
        for name, fld in self.fields.items():
            if name not in new_fields:
                new_fields[name] = fld
        self.fields = new_fields

    def clean(self):
        data = super().clean()
        if not data:
            return data
        p1 = data.get("new_password1") or ""
        p2 = data.get("new_password2") or ""
        is_new = not self.instance.pk
        if is_new:
            if not p1:
                self.add_error("new_password1", "Введите пароль для нового пользователя.")
            if not p2:
                self.add_error("new_password2", "Подтвердите пароль.")
            if p1 and p2 and p1 != p2:
                self.add_error("new_password2", "Пароли не совпадают.")
        else:
            if p1 or p2:
                if p1 != p2:
                    self.add_error("new_password2", "Пароли не совпадают.")
                if p1 and not p2:
                    self.add_error("new_password2", "Введите подтверждение пароля.")
                if p2 and not p1:
                    self.add_error("new_password1", "Введите новый пароль.")
        pwd_for_validation = p1 if (is_new or p1) else None
        if pwd_for_validation:
            tmp_user = (
                self.instance
                if self.instance.pk
                else User(
                    username=(data.get("username") or "").strip(),
                    email=(data.get("email") or "").strip(),
                )
            )
            try:
                validate_password(pwd_for_validation, tmp_user)
            except ValidationError as exc:
                for msg in exc.messages:
                    self.add_error("new_password1", msg)
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get("new_password1")
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
        return user


def _make_django_user_form_class():
    return DjangoUserPanelForm


def _make_user_storage_quota_form_class():
    q_widgets = _widgets_for_model(UserStorageQuota)

    class UserStorageQuotaPanelForm(forms.ModelForm):
        quota_amount = forms.DecimalField(
            label="Размер лимита",
            max_digits=18,
            decimal_places=6,
            min_value=Decimal("0"),
            widget=forms.NumberInput(attrs={"class": "form-control", "step": "any", "min": "0"}),
            help_text=(
                "Укажите число и единицу (КБ / МБ / ГБ). Лимит в базе хранится в байтах и вычисляется автоматически."
            ),
        )
        quota_unit = forms.ChoiceField(
            label="Единица измерения",
            choices=UNIT_LABELS_CHOICES,
            widget=forms.Select(attrs={"class": "form-select"}),
        )
        used_display = forms.CharField(
            label="Занято в хранилище",
            required=False,
            disabled=True,
            widget=forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
        )

        class Meta:
            model = UserStorageQuota
            fields = ("user",)

        def __init__(self, *args, quota_limits_locked=False, **kwargs):
            self._quota_limits_locked = quota_limits_locked
            super().__init__(*args, **kwargs)
            self.fields["user"].widget = q_widgets["user"]
            if self.instance and self.instance.pk:
                self.fields["user"].disabled = True
                tb = int(self.instance.total_quota_bytes or 0)
                amt, unit = bytes_to_amount_unit(tb)
                self.initial.setdefault("quota_amount", amt)
                self.initial.setdefault("quota_unit", unit)
                self.initial["used_display"] = format_bytes_ru(int(self.instance.used_bytes or 0))
            else:
                default_b = int(UserStorageQuota._meta.get_field("total_quota_bytes").default or 0)
                amt, unit = bytes_to_amount_unit(default_b)
                self.initial.setdefault("quota_amount", amt)
                self.initial.setdefault("quota_unit", unit)
                self.initial["used_display"] = "— (новая запись)"

            if quota_limits_locked:
                self.fields["quota_amount"].disabled = True
                self.fields["quota_unit"].disabled = True
                self.fields["quota_amount"].required = False
                self.fields["quota_unit"].required = False
                self.fields["quota_amount"].help_text = (
                    "Изменение лимита недоступно в текущей конфигурации хранилища (не локальный бэкенд по умолчанию "
                    "или облачный режим)."
                )

        def clean(self):
            cleaned_data = super().clean()
            if self._quota_limits_locked:
                if self.instance.pk:
                    tb = int(self.instance.total_quota_bytes or 0)
                    amt, unit = bytes_to_amount_unit(tb)
                    cleaned_data["quota_amount"] = amt
                    cleaned_data["quota_unit"] = unit
                else:
                    default_b = int(UserStorageQuota._meta.get_field("total_quota_bytes").default or 0)
                    amt, unit = bytes_to_amount_unit(default_b)
                    cleaned_data["quota_amount"] = amt
                    cleaned_data["quota_unit"] = unit
            else:
                amt = cleaned_data.get("quota_amount")
                unit = cleaned_data.get("quota_unit")
                if amt is not None and unit:
                    try:
                        cleaned_data["_total_quota_bytes_parsed"] = parse_quota_to_bytes(amt, unit)
                    except ValueError as exc:
                        raise forms.ValidationError(str(exc)) from exc
            return cleaned_data

        def save(self, commit=True):
            obj = super().save(commit=False)
            if self._quota_limits_locked:
                if obj.pk:
                    obj.refresh_from_db(fields=["total_quota_bytes", "used_bytes"])
                else:
                    obj.total_quota_bytes = int(
                        UserStorageQuota._meta.get_field("total_quota_bytes").default or 0
                    )
            else:
                parsed = self.cleaned_data.get("_total_quota_bytes_parsed")
                if parsed is not None:
                    obj.total_quota_bytes = parsed
            if commit:
                obj.save()
            return obj

    return UserStorageQuotaPanelForm


def _make_file_panel_form_class():
    skip = {"extracted_text", "has_preview", "download_count"}
    field_names: list[str] = []
    for f in File._meta.fields:
        if f.name in skip:
            continue
        field_names.append(f.name)
    m2m = [f.name for f in File._meta.many_to_many]
    all_fields = tuple(field_names + m2m)
    widgets = _widgets_for_model(File)
    for name in m2m:
        if name not in widgets:
            widgets[name] = forms.SelectMultiple(attrs={"class": "form-select", "size": "8"})

    class FilePanelForm(forms.ModelForm):
        class Meta:
            model = File
            fields = all_fields
            widgets = widgets

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields["file_size"].disabled = True
            self.fields["version"].disabled = True

    return FilePanelForm


def _make_external_connection_form_class():
    class ExternalStorageConnectionPanelForm(forms.ModelForm):
        class Meta:
            model = ExternalStorageConnection
            fields = ("user", "provider", "expires_at")
            widgets = {
                "user": forms.Select(attrs={"class": "form-select"}),
                "provider": forms.Select(attrs={"class": "form-select"}),
                "expires_at": forms.DateTimeInput(
                    attrs={"class": "form-control", "type": "datetime-local"}
                ),
            }

    return ExternalStorageConnectionPanelForm


def _make_model_form(model: type[models.Model]):
    if model is User:
        return _make_django_user_form_class()
    if model is UserStorageQuota:
        return _make_user_storage_quota_form_class()
    if model is File:
        return _make_file_panel_form_class()
    if model is ExternalStorageConnection:
        return _make_external_connection_form_class()
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


def _apply_filters(request, qs, config: PanelModelConfig):
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


def _ordering(model: type[models.Model], config: PanelModelConfig, request):
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


def _column_header(model: type[models.Model], field_name: str) -> str:
    try:
        f = model._meta.get_field(field_name)
        return str(f.verbose_name)
    except FieldDoesNotExist:
        return field_name.replace("_", " ")


def _cell_display(obj, field_name: str, model: type[models.Model] | None = None):
    if (
        model is UserStorageQuota
        and field_name in ("total_quota_bytes", "used_bytes")
    ):
        try:
            raw = getattr(obj, field_name)
            return format_bytes_ru(int(raw))
        except (TypeError, ValueError):
            return "—"
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
def fm_admin_index(request):
    _require_fm_admin(request.user)
    apps_models = []
    for name, cfg in sorted(
        FM_ADMIN_REGISTRY.items(),
        key=lambda x: display_label(x[1]).lower(),
    ):
        if name == "django_user" and not _can_manage_django_users(request.user):
            continue
        model = cfg.model
        count = model.objects.count()
        apps_models.append(
            {
                "key": name,
                "verbose_name": display_label(cfg),
                "count": count,
                "changelist_url": reverse(
                    "file_manager:fm_core_admin_changelist",
                    kwargs={"model_name": name},
                ),
            }
        )
    django_users_url = reverse(
        "file_manager:fm_core_admin_changelist",
        kwargs={"model_name": "django_user"},
    )
    return render(
        request,
        "file_manager/core_admin/index.html",
        {
            "apps_models": apps_models,
            "django_users_url": django_users_url,
            "local_quota_editable": _local_file_quota_editable(),
        },
    )


@login_required
def fm_admin_changelist(request, model_name: str):
    _require_fm_admin(request.user)
    if model_name == "django_user":
        _require_django_user_admin(request.user)

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
        rows.append(
            {
                "obj": obj,
                "cells": [_cell_display(obj, col, model) for col in config.list_display],
            }
        )

    list_display_headers = [_column_header(model, col) for col in config.list_display]

    context = {
        "config": config,
        "model_name": model_name,
        "verbose_name_plural": display_label(config),
        "page_obj": page_obj,
        "q": q,
        "list_display": config.list_display,
        "list_display_headers": list_display_headers,
        "filter_choices": filter_choices,
        "ordering": ordering,
        "rows": rows,
        "add_url": reverse("file_manager:fm_core_admin_add", kwargs={"model_name": model_name}),
        "show_add_button": config.allow_add,
    }
    return render(request, "file_manager/core_admin/changelist.html", context)


@login_required
@require_http_methods(["POST"])
def fm_admin_bulk_delete(request, model_name: str):
    _require_fm_admin(request.user)
    if model_name == "django_user":
        _require_django_user_admin(request.user)

    config = get_config(model_name)
    if not config:
        raise Http404
    model = config.model
    ids = request.POST.getlist("_selected_action")
    if not ids:
        messages.warning(request, "Не выбраны объекты для удаления.")
        return redirect("file_manager:fm_core_admin_changelist", model_name=model_name)
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
    return redirect("file_manager:fm_core_admin_changelist", model_name=model_name)


@login_required
def fm_admin_add(request, model_name: str):
    _require_fm_admin(request.user)
    if model_name == "django_user":
        _require_django_user_admin(request.user)

    config = get_config(model_name)
    if not config:
        raise Http404
    if not config.allow_add:
        raise PermissionDenied
    model = config.model
    FormClass = _make_model_form(model)
    quota_form_kw = {}
    if model is UserStorageQuota:
        quota_form_kw["quota_limits_locked"] = not _local_file_quota_editable()

    if request.method == "POST":
        form = FormClass(request.POST, request.FILES, **quota_form_kw)
        if form.is_valid():
            try:
                obj = form.save()
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, f"Объект «{obj}» создан.")
                return redirect(
                    "file_manager:fm_core_admin_change",
                    model_name=model_name,
                    object_id=obj.pk,
                )
    else:
        form = FormClass(**quota_form_kw)

    quota_locked = model is UserStorageQuota and not _local_file_quota_editable()

    return render(
        request,
        "file_manager/core_admin/change_form.html",
        {
            "config": config,
            "model_name": model_name,
            "verbose_name": model._meta.verbose_name,
            "model_verbose_name_plural": display_label(config),
            "form": form,
            "object": None,
            "is_add": True,
            "changelist_url": reverse(
                "file_manager:fm_core_admin_changelist",
                kwargs={"model_name": model_name},
            ),
            "quota_limits_locked": quota_locked,
            "local_quota_editable": _local_file_quota_editable(),
            "quota_last_updated": None,
        },
    )


@login_required
def fm_admin_change(request, model_name: str, object_id: int):
    _require_fm_admin(request.user)
    if model_name == "django_user":
        _require_django_user_admin(request.user)

    config = get_config(model_name)
    if not config:
        raise Http404
    model = config.model
    obj = get_object_or_404(model, pk=object_id)
    FormClass = _make_model_form(model)
    quota_form_kw = {}
    if model is UserStorageQuota:
        quota_form_kw["quota_limits_locked"] = not _local_file_quota_editable()

    if request.method == "POST":
        form = FormClass(request.POST, request.FILES, instance=obj, **quota_form_kw)
        if form.is_valid():
            try:
                form.save()
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                if model is UserStorageQuota:
                    try:
                        obj.refresh_from_db()
                        obj.update_usage()
                    except Exception:
                        pass
                messages.success(request, "Изменения сохранены.")
                return redirect(
                    "file_manager:fm_core_admin_change",
                    model_name=model_name,
                    object_id=object_id,
                )
    else:
        form = FormClass(instance=obj, **quota_form_kw)

    django_meta = None
    if model is User:
        django_meta = {
            "date_joined": obj.date_joined,
            "last_login": obj.last_login,
        }

    return render(
        request,
        "file_manager/core_admin/change_form.html",
        {
            "config": config,
            "model_name": model_name,
            "verbose_name": model._meta.verbose_name,
            "model_verbose_name_plural": display_label(config),
            "form": form,
            "object": obj,
            "is_add": False,
            "changelist_url": reverse(
                "file_manager:fm_core_admin_changelist",
                kwargs={"model_name": model_name},
            ),
            "delete_url": reverse(
                "file_manager:fm_core_admin_delete",
                kwargs={"model_name": model_name, "object_id": object_id},
            ),
            "django_user_meta": django_meta,
            "quota_limits_locked": model is UserStorageQuota and not _local_file_quota_editable(),
            "local_quota_editable": _local_file_quota_editable(),
            "quota_last_updated": obj.last_updated if model is UserStorageQuota else None,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def fm_admin_delete(request, model_name: str, object_id: int):
    _require_fm_admin(request.user)
    if model_name == "django_user":
        _require_django_user_admin(request.user)

    config = get_config(model_name)
    if not config:
        raise Http404
    model = config.model
    obj = get_object_or_404(model, pk=object_id)
    if request.method == "POST":
        label = str(obj)
        obj.delete()
        messages.success(request, f"Удалено: {label}")
        return redirect("file_manager:fm_core_admin_changelist", model_name=model_name)
    return render(
        request,
        "file_manager/core_admin/delete_confirmation.html",
        {
            "config": config,
            "model_name": model_name,
            "object": obj,
            "verbose_name": model._meta.verbose_name,
            "model_verbose_name_plural": display_label(config),
            "changelist_url": reverse(
                "file_manager:fm_core_admin_changelist",
                kwargs={"model_name": model_name},
            ),
        },
    )


