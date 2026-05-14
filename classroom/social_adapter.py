"""
Адаптер django-allauth: подробные логи входа через Яндекс без утечки секретов.
Логгер: classroom.yandex_oauth (уровень задаётся DJANGO_YANDEX_OAUTH_LOG_LEVEL).
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

logger = logging.getLogger("classroom.yandex_oauth")


def _site_domain(request) -> str:
    try:
        if request is not None:
            return getattr(get_current_site(request), "domain", "?")
        from django.contrib.sites.models import Site

        return Site.objects.get(pk=getattr(settings, "SITE_ID", 1)).domain
    except Exception as exc:
        return f"<site:{type(exc).__name__}>"


def _oauth_query_summary(request) -> dict[str, Any]:
    g = request.GET
    summary: dict[str, Any] = {
        "has_code": bool(g.get("code")),
        "has_state": bool(g.get("state")),
    }
    if "error" in g:
        summary["oauth_error"] = g.get("error")
        desc = g.get("error_description") or ""
        if isinstance(desc, str):
            summary["oauth_error_description"] = desc[:400]
        else:
            summary["oauth_error_description"] = str(desc)[:400]
    return summary


def _extra_context_summary(extra: dict | None) -> dict[str, Any]:
    if not extra:
        return {}
    out: dict[str, Any] = {}
    for key, val in extra.items():
        if key == "state" and isinstance(val, dict):
            out["state_keys"] = sorted(val.keys())
        elif key == "state_id":
            out["state_id_present"] = bool(val)
        elif key == "callback_view":
            out["callback_view"] = val.__class__.__name__
        else:
            out[key] = type(val).__name__
    return out


def _yandex_callback_abs(request) -> str:
    try:
        return request.build_absolute_uri(reverse("yandex_callback"))
    except Exception as exc:
        return f"<url:{type(exc).__name__}:{exc}>"


def _mask_email(email: object) -> str:
    if not email or not isinstance(email, str):
        return ""
    at = email.find("@")
    if at <= 0:
        return "***"
    return email[0] + "***@" + email[at + 1 :]


class LoggingSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if sociallogin.account.provider != "yandex":
            return super().pre_social_login(request, sociallogin)

        extra = sociallogin.account.extra_data or {}
        uid = sociallogin.account.uid or extra.get("id", "")
        email = (
            extra.get("default_email")
            or extra.get("email")
            or getattr(sociallogin.user, "email", "")
            or ""
        )
        cid = (getattr(settings, "YANDEX_AUTH_CLIENT_ID", "") or "").strip()
        logger.info(
            "yandex pre_social_login uid=%s email=%s is_existing_social=%s "
            "request_user_pk=%s site_domain=%s request_host=%s "
            "session_key=%s yandex_callback_url=%s client_id_configured=%s client_id_prefix=%s",
            uid,
            _mask_email(str(email)),
            sociallogin.is_existing,
            getattr(request.user, "pk", None) or None,
            _site_domain(request),
            request.get_host(),
            bool(request.session.session_key),
            _yandex_callback_abs(request),
            bool(cid),
            cid[:12] + "…" if len(cid) > 12 else cid,
        )
        return super().pre_social_login(request, sociallogin)

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        if sociallogin.account.provider == "yandex":
            logger.info(
                "yandex social user saved user_pk=%s username=%s",
                user.pk,
                getattr(user, "username", ""),
            )
        return user

    def on_authentication_error(
        self,
        request,
        provider,
        error=None,
        exception=None,
        extra_context=None,
    ):
        pid = getattr(provider, "id", provider)
        if pid == "yandex":
            logger.warning(
                "yandex social auth FAILED error_code=%r exception_type=%s exception_msg=%s "
                "path=%s site_domain=%s host=%s query=%s extra=%s",
                error,
                type(exception).__name__ if exception else None,
                (str(exception)[:500] if exception else ""),
                getattr(request, "path", ""),
                _site_domain(request) if request else "",
                request.get_host() if request else "",
                _oauth_query_summary(request) if request else {},
                _extra_context_summary(extra_context),
                exc_info=exception is not None,
            )
            if exception is not None:
                low = str(exception).lower()
                if any(
                    s in low
                    for s in (
                        "network is unreachable",
                        "no route to host",
                        "name or service not known",
                        "temporary failure in name resolution",
                        "connection refused",
                        "timed out",
                        "failed to resolve",
                    )
                ):
                    logger.warning(
                        "yandex_oauth hint: из процесса Django нет рабочего исходящего HTTPS "
                        "до oauth.yandex.ru — проверьте файрвол хоста, маршрутизацию/VPN, DNS. "
                        "В docker-compose.yml для web задан network_mode: host (Linux); "
                        "на Docker Desktop при необходимости переключите web на bridge вручную."
                    )
        return super().on_authentication_error(
            request,
            provider,
            error=error,
            exception=exception,
            extra_context=extra_context,
        )
