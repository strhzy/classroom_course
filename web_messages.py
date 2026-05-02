"""Унификация flash-сообщений для шаблона base.html (тосты)."""
from django.contrib import messages


def flash_form_errors(request, form):
    """Передаёт ошибки валидации формы в Django messages (показ в toast)."""
    if not form.errors:
        return
    for name, err_list in form.errors.items():
        for err in err_list:
            if name == "__all__":
                messages.error(request, err)
            else:
                fld = form.fields.get(name)
                label = fld.label if fld and fld.label else name
                messages.error(request, f"{label}: {err}")
