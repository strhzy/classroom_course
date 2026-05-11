"""Человекочитаемые единицы (КБ/МБ/ГБ) для квот хранилища; перевод в байты для поля БД."""

from __future__ import annotations

from decimal import Decimal

# Двоичные единицы (как в ОС и отображении дисков)
UNIT_MULTIPLIER: dict[str, int] = {
    "KB": 1024,
    "MB": 1024**2,
    "GB": 1024**3,
}

UNIT_LABELS_CHOICES: tuple[tuple[str, str], ...] = (
    ("KB", "КБ (килобайт, 1024 байт)"),
    ("MB", "МБ (мегабайт, 1024² байт)"),
    ("GB", "ГБ (гигабайт, 1024³ байт)"),
)


def bytes_to_amount_unit(total_bytes: int) -> tuple[Decimal, str]:
    """
    Подбирает удобную единицу и число для отображения/редактирования.
    Возвращает (значение, код единицы: KB | MB | GB).
    """
    if total_bytes < 0:
        total_bytes = 0
    if total_bytes == 0:
        return Decimal("0"), "MB"

    b = Decimal(total_bytes)
    gb = b / Decimal(UNIT_MULTIPLIER["GB"])
    if gb >= 1:
        return gb.quantize(Decimal("0.01")), "GB"
    mb = b / Decimal(UNIT_MULTIPLIER["MB"])
    if mb >= 1:
        return mb.quantize(Decimal("0.01")), "MB"
    kb = b / Decimal(UNIT_MULTIPLIER["KB"])
    return kb.quantize(Decimal("0.01")), "KB"


def parse_quota_to_bytes(amount: Decimal | float | str, unit: str) -> int:
    """Переводит введённое число и единицу в целое число байт."""
    u = (unit or "MB").upper()
    if u not in UNIT_MULTIPLIER:
        raise ValueError(f"Неизвестная единица: {unit!r}")
    a = Decimal(str(amount))
    if a < 0:
        a = Decimal("0")
    raw = a * Decimal(UNIT_MULTIPLIER[u])
    return int(raw.quantize(Decimal("1")))


def format_bytes_ru(n: int) -> str:
    """Краткое отображение размера (байт, КБ, МБ, ГБ, ТБ)."""
    if n < 0:
        n = 0
    if n < 1024:
        return f"{n} байт"
    v = float(n)
    labels = ["байт", "КБ", "МБ", "ГБ", "ТБ"]
    idx = 0
    while v >= 1024 and idx < len(labels) - 1:
        v /= 1024.0
        idx += 1
    if idx == 0:
        return f"{int(v)} {labels[idx]}"
    return f"{v:.2f} {labels[idx]}".replace(".", ",")
