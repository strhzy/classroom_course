"""
Проверка загружаемых файлов через ClamAV (clamd).

Настройки (classroom/settings.py и .env):
  CLAMAV_ENABLED — включить проверку (по умолчанию выключено).
  CLAMAV_FAIL_OPEN — если True и демон недоступен, файл всё равно принимается (с предупреждением).
  CLAMAV_SOCKET_PATH — сокет Unix clamd.
  CLAMAV_USE_TCP / CLAMAV_TCP_HOST / CLAMAV_TCP_PORT — альтернатива TCP.
"""
from __future__ import annotations

import io
import logging
import time
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def _scan_log_ctx(
    size: int,
    user_id: int | None = None,
    filename: str | None = None,
) -> str:
    parts = [f"size_bytes={size}"]
    if user_id is not None:
        parts.append(f"user_id={user_id}")
    if filename is not None:
        parts.append(f"filename={filename!r}")
    return " ".join(parts)


def _log_scan_outcome(
    out: dict[str, Any],
    started: float,
    size: int,
    user_id: int | None,
    filename: str | None,
) -> None:
    duration_ms = (time.monotonic() - started) * 1000
    ctx = _scan_log_ctx(size, user_id=user_id, filename=filename)
    if out.get("performed") and out.get("clean") is True:
        logger.info("clamav scan clean %s duration_ms=%.1f", ctx, duration_ms)
        return
    if out.get("performed") and out.get("clean") is False:
        threat = out.get("threat") or "unknown"
        logger.warning(
            "clamav scan threat=%s %s duration_ms=%.1f",
            threat,
            ctx,
            duration_ms,
        )
        return
    if out.get("performed"):
        logger.warning(
            "clamav scan inconclusive error=%r %s duration_ms=%.1f",
            out.get("error"),
            ctx,
            duration_ms,
        )


def scan_upload_bytes(
    data: bytes,
    *,
    user_id: int | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    """
    Результат проверки байтов файла.

    Ключи:
      performed — была ли попытка реальной проверки clamd
      clean — True / False / None (None если проверки не было)
      threat — имя сигнатуры при clean=False
      error — текст ошибки демона / модуля
      skipped — короткий код причины пропуска
    """
    size = len(data)
    ctx = _scan_log_ctx(size, user_id=user_id, filename=filename)

    if not getattr(settings, "CLAMAV_ENABLED", False):
        logger.debug("clamav skipped (disabled) %s", ctx)
        return {
            "performed": False,
            "clean": None,
            "threat": None,
            "error": None,
            "skipped": "disabled",
        }

    try:
        import clamd
    except ImportError:
        err = "Пакет clamd не установлен (pip install clamd)"
        logger.error("clamav %s %s", err, ctx)
        if getattr(settings, "CLAMAV_FAIL_OPEN", True):
            logger.info("clamav accept without scan (fail_open) skipped=no_module %s", ctx)
            return {
                "performed": False,
                "clean": None,
                "threat": None,
                "error": err,
                "skipped": "no_module",
            }
        return {
            "performed": False,
            "clean": None,
            "threat": None,
            "error": err,
            "skipped": "no_module",
        }

    client = _make_clamd_client()
    if client is None:
        err = "Не удалось подключиться к clamd (проверьте сокет или TCP)"
        logger.warning("clamav %s %s", err, ctx)
        if getattr(settings, "CLAMAV_FAIL_OPEN", True):
            logger.info("clamav accept without scan (fail_open) skipped=daemon %s", ctx)
            return {
                "performed": False,
                "clean": None,
                "threat": None,
                "error": err,
                "skipped": "daemon",
            }
        return {
            "performed": False,
            "clean": None,
            "threat": None,
            "error": err,
            "skipped": "daemon",
        }

    t0 = time.monotonic()
    try:
        result = client.instream(io.BytesIO(data))
    except Exception as exc:
        logger.exception("clamav instream failed %s", ctx)
        if getattr(settings, "CLAMAV_FAIL_OPEN", True):
            logger.info("clamav accept without scan (fail_open) skipped=scan_error %s", ctx)
            return {
                "performed": False,
                "clean": None,
                "threat": None,
                "error": str(exc),
                "skipped": "scan_error",
            }
        return {
            "performed": False,
            "clean": None,
            "threat": None,
            "error": str(exc),
            "skipped": "scan_error",
        }

    out = _interpret_clamd_result(result)
    _log_scan_outcome(out, t0, size, user_id, filename)
    return out


def _make_clamd_client():
    import clamd

    if getattr(settings, "CLAMAV_USE_TCP", False):
        host = getattr(settings, "CLAMAV_TCP_HOST", "127.0.0.1")
        port = int(getattr(settings, "CLAMAV_TCP_PORT", 3310))
        try:
            return clamd.ClamdNetworkSocket(host=host, port=port)
        except Exception as exc:
            logger.warning("ClamdNetworkSocket: %s", exc)
            return None

    path = getattr(
        settings,
        "CLAMAV_SOCKET_PATH",
        "/var/run/clamav/clamd.ctl",
    )
    try:
        return clamd.ClamdUnixSocket(path)
    except Exception as exc:
        logger.warning("ClamdUnixSocket(%s): %s", path, exc)
        return None


def _interpret_clamd_result(result) -> dict[str, Any]:
    """Разбор ответа clamd.instream.

    Варианты: {'stream': 'OK'}, {'stream': ('OK', None)} (некоторые версии python-clamd),
    {'stream': ('FOUND', sig)}.
    """
    if not result:
        return {
            "performed": True,
            "clean": False,
            "threat": None,
            "error": "Пустой ответ clamd",
            "skipped": None,
        }

    if isinstance(result, dict):
        stream = result.get("stream")
        if stream == "OK" or (
            isinstance(stream, tuple) and len(stream) >= 1 and stream[0] == "OK"
        ):
            return {
                "performed": True,
                "clean": True,
                "threat": None,
                "error": None,
                "skipped": None,
            }
        if isinstance(stream, tuple) and len(stream) >= 2 and stream[0] == "FOUND":
            return {
                "performed": True,
                "clean": False,
                "threat": str(stream[1]),
                "error": None,
                "skipped": None,
            }
        if isinstance(stream, str) and stream.startswith("FOUND"):
            sig = stream.replace("FOUND", "", 1).strip()
            return {
                "performed": True,
                "clean": False,
                "threat": sig or "unknown",
                "error": None,
                "skipped": None,
            }

    if isinstance(result, (tuple, list)) and len(result) >= 2:
        part = result[1]
        if part == "OK":
            return {
                "performed": True,
                "clean": True,
                "threat": None,
                "error": None,
                "skipped": None,
            }
        if isinstance(part, (tuple, list)) and len(part) >= 2 and part[0] == "FOUND":
            return {
                "performed": True,
                "clean": False,
                "threat": str(part[1]),
                "error": None,
                "skipped": None,
            }
        if isinstance(part, str) and part == "OK":
            return {
                "performed": True,
                "clean": True,
                "threat": None,
                "error": None,
                "skipped": None,
            }

    logger.warning("Неожиданный ответ clamd: %r", result)
    return {
        "performed": True,
        "clean": False,
        "threat": None,
        "error": f"Не удалось разобрать ответ: {result!r}",
        "skipped": None,
    }


def flash_scan_followup(request, scan: dict[str, Any]) -> None:
    """Доп. сообщения после успешного сохранения файла (инфо / предупреждение о проверке)."""
    from django.contrib import messages

    if not scan:
        return
    if scan.get("performed") and scan.get("clean"):
        messages.info(
            request,
            "Антивирусная проверка (ClamAV): угроз не обнаружено.",
        )
        return
    if getattr(settings, "CLAMAV_ENABLED", False) and not scan.get("performed"):
        detail = scan.get("error") or "служба недоступна"
        messages.warning(
            request,
            f"Файл сохранён без антивирусной проверки: {detail}. "
            "Если политика организации требует проверку — обратитесь к администратору.",
        )
