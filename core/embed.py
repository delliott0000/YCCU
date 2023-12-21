from __future__ import annotations
from typing import TYPE_CHECKING

from dataclasses import dataclass

from discord import Embed

if TYPE_CHECKING:
    from typing import Any, Self


@dataclass(kw_only=True, slots=True, frozen=True)
class EmbedField:

    name: Any
    value: Any
    inline: bool = True

    def __len__(self) -> int:
        return len(str(self.name)) + len(str(self.value))


class CustomEmbed(Embed):

    __slots__ = ()

    def add_custom_field(self, field: EmbedField, /) -> Self:
        return self.add_field(name=field.name, value=field.value, inline=field.inline)

    def reverse_fields(self) -> None:
        try:
            self._fields.reverse()
        except AttributeError:
            pass
