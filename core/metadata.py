from __future__ import annotations
from typing import TYPE_CHECKING

from dataclasses import dataclass

if TYPE_CHECKING:
    from core.bot import CustomBot


@dataclass(kw_only=True, slots=True)
class MetaData:

    bot: CustomBot

    logging_channel_id: int | None
    general_channel_id: int | None

    admin_role_id: int | None
    bot_role_id: int | None
    senior_role_id: int | None
    hmod_role_id: int | None
    smod_role_id: int | None
    rmod_role_id: int | None
    tmod_role_id: int | None
    helper_role_id: int | None
    active_role_id: int | None

    domain_bl: list[str]
    domain_wl: list[str]

    event_ignored_role_ids: list[int]
    automod_ignored_role_ids: list[int]
    event_ignored_channel_ids: list[int]
    automod_ignored_channel_ids: list[int]

    activity: str | None
    greeting: str | None
    appeal_url: str | None
