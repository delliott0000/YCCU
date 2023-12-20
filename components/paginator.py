from __future__ import annotations
from typing import TYPE_CHECKING

from discord.ui import View, button
from discord import ButtonStyle, HTTPException

if TYPE_CHECKING:
    from discord.ui import Button
    from discord import User, Member, Message, Embed, Interaction

    AuthorType = User | Member | None


class Paginator(View):

    def __init__(self, author: AuthorType, message: Message, embeds: list[Embed], /) -> None:
        super().__init__(timeout=120)
        self.author: AuthorType = author
        self.message: Message = message
        self.embeds: list[Embed] = embeds
        self.current_page: int = 1
        self.update_buttons()

    def update_buttons(self) -> None:
        for child in self.children:
            child: Button
            child.disabled = True
        self.firs_page.disabled = self.prev_page.disabled = self.current_page == 1
        self.last_page.disabled = self.next_page.disabled = self.current_page == len(self.embeds)

    async def edit_page(self, interaction: Interaction, /) -> None:
        await interaction.response.defer() # noqa
        self.update_buttons()
        await self.message.edit(embed=self.embeds[self.current_page - 1], view=self)

    @button(label='<<')
    async def firs_page(self, interaction: Interaction, _: Button, /) -> None:
        self.current_page = 1
        await self.edit_page(interaction)

    @button(label='<', style=ButtonStyle.blurple)
    async def prev_page(self, interaction: Interaction, _: Button, /) -> None:
        self.current_page -= 1
        await self.edit_page(interaction)

    @button(label='>', style=ButtonStyle.blurple)
    async def next_page(self, interaction: Interaction, _: Button, /) -> None:
        self.current_page += 1
        await self.edit_page(interaction)

    @button(label='>>')
    async def last_page(self, interaction: Interaction, _: Button, /) -> None:
        self.current_page = len(self.embeds)
        await self.edit_page(interaction)

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if self.author is not None and interaction.user != self.author:
            await interaction.response.send_message('You can\'t use that.', ephemeral=True) # noqa
            return False
        return True

    async def on_timeout(self) -> None:
        try:
            await self.message.edit(view=None)
        except HTTPException:
            pass
