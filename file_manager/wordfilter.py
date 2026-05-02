"""
Проверка извлечённого текста файла по словарю static/file_manager/words.txt.

Формат файла: одна запись на строку; `#` — комментарий до конца строки.
Пустые строки игнорируются. Одно слово ищется как целое слово (регистр не важен);
если в строке есть пробел — фраза ищется как подстрока (регистр не важен).
"""
from __future__ import annotations

import logging
import os
import re

from django.contrib.staticfiles import finders

logger = logging.getLogger(__name__)

STATIC_REL_PATH = "file_manager/words.txt"

_mtime_cache: float | None = None
_words_cache: frozenset[str] | None = None


def _read_words_file(path: str) -> frozenset[str]:
    out: list[str] = []
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.split("#", 1)[0].strip()
                if line:
                    out.append(line)
    except OSError as exc:
        logger.warning("wordfilter: не удалось прочитать %s: %s", path, exc)
        return frozenset()
    return frozenset(out)


def load_banned_entries() -> frozenset[str]:
    """Слова/фразы из words.txt; при отсутствии файла — пустой набор."""
    global _mtime_cache, _words_cache
    path = finders.find(STATIC_REL_PATH)
    if not path:
        return frozenset()
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return frozenset()
    if _words_cache is not None and _mtime_cache == mtime:
        return _words_cache
    words = _read_words_file(path)
    _mtime_cache = mtime
    _words_cache = words
    return words


def find_banned_match(text: str) -> str | None:
    """
    Возвращает первую найденную запись из словаря, если она встречается в text, иначе None.
    """
    if not text or not text.strip():
        return None
    entries = load_banned_entries()
    if not entries:
        return None
    lowered_full = text.lower()
    for entry in sorted(entries, key=len, reverse=True):
        e = entry.strip()
        if not e:
            continue
        if " " in e:
            if e.lower() in lowered_full:
                return entry
            continue
        try:
            pattern = re.compile(
                r"(?<!\w)" + re.escape(e) + r"(?!\w)",
                re.IGNORECASE | re.UNICODE,
            )
        except re.error:
            continue
        if pattern.search(text):
            return entry
    return None
