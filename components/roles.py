from __future__ import annotations
from typing import TYPE_CHECKING

from resources.emojis import ROLE_ICON

from discord.ui import Button, View
from discord import Colour, HTTPException, Embed

if TYPE_CHECKING:
    from discord import Role, Interaction


class RoleButton(Button):

    def __init__(self, role: Role, /) -> None:
        super().__init__(label=role.name, emoji=ROLE_ICON, custom_id=f'r{role.id}')
        self.role: Role = role

    async def callback(self, interaction: Interaction, /) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True) # noqa

        try:
            if self.role in interaction.user.roles:
                await interaction.user.remove_roles(self.role)
                message = f'*{self.role.mention} removed.*'
            else:
                await interaction.user.add_roles(self.role)
                message = f'*{self.role.mention} added.*'
            colour = Colour.green()

        except (AttributeError, HTTPException) as error:
            message = f'❌ Something went wrong, please contact a member of staff. Error: `{error}`'
            colour = Colour.red()

        embed = Embed(colour=colour, description=message)
        await interaction.followup.send(embed=embed)


class RoleView(View):

    def __init__(self, *roles: Role) -> None:
        super().__init__(timeout=None)
        for role in roles:
            if len(self.children) <= 25:
                self.add_item(RoleButton(role))
            else:
                break
