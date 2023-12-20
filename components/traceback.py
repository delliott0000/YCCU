from __future__ import annotations
from typing import TYPE_CHECKING

from discord.ui import View, button
from discord import HTTPException

if TYPE_CHECKING:
    from core.bot import CustomBot

    from discord.ui import Button
    from discord import Message, Interaction


class TracebackView(View):

    def __init__(self, bot: CustomBot, message: Message, traceback: str, /) -> None:
        super().__init__(timeout=86400)
        self.bot: CustomBot = bot
        self.message: Message = message
        self.traceback: str = traceback

    @button(label='Full Traceback')
    async def view_traceback(self, interaction: Interaction, _: Button, /) -> None:
        await interaction.response.send_message(self.traceback, ephemeral=True) # noqa

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if await self.bot.member_clearance(interaction.user) < 9:
            await interaction.response.send_message('You can\'t use that.', ephemeral=True) # noqa
            return False
        return True

    async def on_timeout(self) -> None:
        try:
            await self.message.edit(view=None)
        except HTTPException:
            pass
