"""Фильтры шаблонов для проверки прав на объектах курса."""

from django import template

register = template.Library()


@register.filter
def allows_edit(obj, user):
    """Вызов obj.can_edit(user), если метод есть."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    fn = getattr(obj, "can_edit", None)
    if callable(fn):
        return bool(fn(user))
    return False


@register.filter
def allows_course_delete(course, user):
    """Вызов course.can_delete(user)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    fn = getattr(course, "can_delete", None)
    if callable(fn):
        return bool(fn(user))
    return False
