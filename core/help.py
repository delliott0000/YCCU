from __future__ import annotations
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import CustomContext


class CustomHelpCommand(commands.HelpCommand):

    context: CustomContext
