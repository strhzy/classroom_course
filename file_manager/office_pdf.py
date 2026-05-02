"""
Конвертация Word/Excel и др. в PDF для просмотрщика.

Порядок:
1. ConvertAPI (если задан CONVERTAPI_SECRET / settings.CONVERTAPI_SECRET).
2. LibreOffice в headless-режиме (локально, без оплаты API).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings

EXTENSIONS_LIBREOFFICE_TO_PDF = frozenset(
    {"doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp", "rtf"}
)


def get_convertapi_secret() -> str:
    return (
        getattr(settings, "CONVERTAPI_SECRET", None)
        or os.getenv("CONVERTAPI_SECRET", "")
        or ""
    ).strip()


def is_convertapi_configured() -> bool:
    return bool(get_convertapi_secret())


def get_libreoffice_executable() -> str | None:
    override = getattr(settings, "LIBREOFFICE_PATH", "") or ""
    override = override.strip()
    if override and os.path.isfile(override) and os.access(override, os.X_OK):
        return override
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    mac = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    if os.path.isfile(mac) and os.access(mac, os.X_OK):
        return mac
    return None


def is_libreoffice_available() -> bool:
    return get_libreoffice_executable() is not None


def is_office_pdf_conversion_available() -> bool:
    """Есть хотя бы один способ получить PDF из офисных файлов."""
    return is_convertapi_configured() or is_libreoffice_available()


def _convert_libreoffice_to_pdf_bytes(src_path: str, exe: str) -> bytes:
    if not os.path.isfile(src_path):
        raise FileNotFoundError(src_path)
    with tempfile.TemporaryDirectory(prefix="lo_pdf_") as tmpdir:
        cmd = [
            exe,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            tmpdir,
            os.path.abspath(src_path),
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                timeout=240,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("Конвертация в PDF превысила время ожидания.") from e
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or "")[:2000]
            raise RuntimeError(f"LibreOffice завершился с ошибкой: {err}") from e

        pdfs = sorted(Path(tmpdir).glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not pdfs:
            raise RuntimeError("После конвертации PDF не найден.")
        with open(pdfs[0], "rb") as fh:
            return fh.read()


def _convert_convertapi_to_pdf_bytes(src_path: str, secret: str) -> bytes:
    """Официальный клиент https://pypi.org/project/convertapi/"""
    try:
        import convertapi
    except ImportError as e:
        raise RuntimeError(
            "Установите пакет convertapi: pip install convertapi"
        ) from e

    convertapi.api_credentials = secret
    abs_path = os.path.abspath(src_path)
    result = convertapi.convert("pdf", {"File": abs_path})

    out_file = getattr(result, "file", None)
    if out_file is None and getattr(result, "files", None):
        out_file = result.files[0]
    if out_file is None:
        raise RuntimeError("ConvertAPI: в ответе нет файла PDF.")

    fd, tmp_pdf = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        out_file.save(tmp_pdf)
        with open(tmp_pdf, "rb") as fh:
            return fh.read()
    finally:
        try:
            os.unlink(tmp_pdf)
        except OSError:
            pass


def convert_office_file_to_pdf_bytes(src_path: str) -> bytes:
    """
    Конвертирует локальный файл в PDF, возвращает байты PDF.
    Сначала ConvertAPI (если настроен), иначе LibreOffice.
    """
    if not os.path.isfile(src_path):
        raise FileNotFoundError(src_path)

    secret = get_convertapi_secret()
    if secret:
        try:
            return _convert_convertapi_to_pdf_bytes(src_path, secret)
        except Exception as convertapi_err:
            exe = get_libreoffice_executable()
            if exe:
                try:
                    return _convert_libreoffice_to_pdf_bytes(src_path, exe)
                except Exception as lo_err:
                    raise RuntimeError(
                        f"ConvertAPI: {convertapi_err}; LibreOffice: {lo_err}"
                    ) from lo_err
            raise RuntimeError(f"ConvertAPI не удалось, LibreOffice недоступен: {convertapi_err}") from convertapi_err

    exe = get_libreoffice_executable()
    if not exe:
        raise RuntimeError(
            "Нет конвертации в PDF: задайте CONVERTAPI_SECRET (ConvertAPI) "
            "или установите LibreOffice / LIBREOFFICE_PATH."
        )
    return _convert_libreoffice_to_pdf_bytes(src_path, exe)
