import logging
import time

from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template import loader


logger = logging.getLogger(__name__)


class LoggedPasswordResetForm(PasswordResetForm):
    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        started = time.monotonic()
        backend = "django.core.mail.backends.smtp.EmailBackend"
        host = getattr(settings, "EMAIL_HOST", "")
        port = getattr(settings, "EMAIL_PORT", "")
        tls = getattr(settings, "EMAIL_USE_TLS", "")
        ssl = getattr(settings, "EMAIL_USE_SSL", "")
        logger.info(
            "password_reset_email_send_start to=%s backend=%s host=%s port=%s tls=%s ssl=%s from=%s",
            to_email,
            backend,
            host,
            port,
            tls,
            ssl,
            from_email or getattr(settings, "DEFAULT_FROM_EMAIL", ""),
        )
        try:
            subject = loader.render_to_string(subject_template_name, context)
            subject = "".join(subject.splitlines())
            body = loader.render_to_string(email_template_name, context)
            connection = get_connection(
                backend=backend,
                fail_silently=False,
                host=getattr(settings, "EMAIL_HOST", ""),
                port=getattr(settings, "EMAIL_PORT", None),
                username=getattr(settings, "EMAIL_HOST_USER", ""),
                password=getattr(settings, "EMAIL_HOST_PASSWORD", ""),
                use_tls=getattr(settings, "EMAIL_USE_TLS", False),
                use_ssl=getattr(settings, "EMAIL_USE_SSL", False),
                timeout=getattr(settings, "EMAIL_TIMEOUT", 30),
            )
            email_message = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=from_email or getattr(settings, "DEFAULT_FROM_EMAIL", ""),
                to=[to_email],
                connection=connection,
            )
            if html_email_template_name:
                html_email = loader.render_to_string(html_email_template_name, context)
                email_message.attach_alternative(html_email, "text/html")
            email_message.send(fail_silently=False)
        except Exception:
            logger.exception(
                "password_reset_email_send_failed to=%s elapsed_ms=%s",
                to_email,
                int((time.monotonic() - started) * 1000),
            )
            raise
        logger.info(
            "password_reset_email_send_success to=%s elapsed_ms=%s",
            to_email,
            int((time.monotonic() - started) * 1000),
        )
