from __future__ import annotations
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import CustomBot, CustomContext


class ModerationCommands(commands.Cog):

    ...


async def setup(bot: CustomBot, /) -> None:
    await bot.add_cog(ModerationCommands())
