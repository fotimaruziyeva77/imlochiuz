"""Telegram bilan bog'liq, lekin aiogram'ga bog'lanmagan yordamchilar.

Alohida modulda turgani uchun tarmoq va token'siz test qilinadi.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Iterable, Protocol

MESSAGE_LIMIT = 4096      # Telegram xabari uchun maksimal uzunlik
FILE_THRESHOLD = 10_000   # bundan uzun natija fayl qilib qaytariladi (F1.7)
COPY_BUTTON_LIMIT = 256   # CopyTextButton matni uchun Telegram cheklovi

# O'girishda o'zgartirilmaydigan entity turlari (F1.8).
PROTECTED_ENTITY_TYPES = frozenset(
    {"url", "email", "mention", "hashtag", "cashtag", "bot_command",
     "code", "pre", "phone_number", "text_mention"}
)


class _Entity(Protocol):
    type: str
    offset: int
    length: int


def _utf16_to_index(text: str) -> list[int]:
    """UTF-16 offset → Python indeksi jadvali (emoji va h.k. uchun)."""
    table = []
    for i, ch in enumerate(text):
        table.append(i)
        if ord(ch) > 0xFFFF:
            table.append(i)
    table.append(len(text))
    return table


def entity_spans(text: str, entities: Iterable[_Entity] | None) -> list[tuple[int, int]]:
    """Telegram entity'laridan himoyalangan oraliqlarni (Python indekslarida)
    hosil qiladi. Telegram offset'lari UTF-16 birliklarida beriladi."""
    if not entities:
        return []
    table = _utf16_to_index(text)
    spans = []
    for ent in entities:
        if getattr(ent.type, "value", ent.type) not in PROTECTED_ENTITY_TYPES:
            continue
        start = ent.offset
        end = ent.offset + ent.length
        if start >= len(table):
            continue
        spans.append((table[start], table[min(end, len(table) - 1)]))
    return spans


def split_text(text: str, limit: int = MESSAGE_LIMIT) -> list[str]:
    """Matnni ``limit``dan oshmaydigan bo'laklarga ajratadi.

    Avval paragraf, keyin qator, keyin bo'sh joy chegarasidan kesishga
    harakat qiladi; iloji bo'lmasa — qat'iy ``limit`` bo'yicha.
    Bo'laklar birlashtirilsa asl matn aynan tiklanadi.
    """
    if not text:
        return []
    chunks = []
    while len(text) > limit:
        window = text[:limit]
        cut = -1
        for sep in ("\n\n", "\n", " "):
            pos = window.rfind(sep)
            if pos > 0:
                cut = pos + len(sep)
                break
        if cut <= 0:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:]
    if text:
        chunks.append(text)
    return chunks


class RateLimiter:
    """Foydalanuvchi bo'yicha sirpanuvchi oyna limiti (bepul tarif:
    30 so'rov/daqiqa). Bitta jarayon xotirasida ishlaydi; gorizontal
    kengayishda Redis'ga ko'chiriladi."""

    def __init__(self, limit: int = 30, window: float = 60.0, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self._clock = clock
        self._hits: dict[int, deque[float]] = {}

    def allow(self, user_id: int) -> bool:
        now = self._clock()
        hits = self._hits.setdefault(user_id, deque())
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        if len(self._hits) > 50_000:
            self._cleanup(now)
        return True

    def _cleanup(self, now: float) -> None:
        stale = [uid for uid, h in self._hits.items() if not h or now - h[-1] >= self.window]
        for uid in stale:
            del self._hits[uid]
