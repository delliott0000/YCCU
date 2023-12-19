from __future__ import annotations
from typing import TYPE_CHECKING

from dataclasses import dataclass

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    from core.bot import CustomBot


@dataclass(kw_only=True, slots=True, frozen=True)
class Modlog:

    bot: CustomBot

    case_id: int
    user_id: int
    mod_id: int

    channel_id: int | None = None

    type: str = 'Unknown'
    reason: str = 'No reason provided.'

    created: datetime
    duration: timedelta | None = None

    received: bool = False
    deleted: bool = False
    active: bool = False

    @property
    def until(self) -> datetime:
        return self.created + self.duration

    @property
    def is_expired(self) -> bool:
        return self.until < self.bot.now
