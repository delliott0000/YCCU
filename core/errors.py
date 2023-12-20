from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class DurationError(Exception):

    def __init__(self, duration: str, /) -> None:
        self.duration: str = duration

    def __str__(self) -> str:
        return f'`{self.duration}` is not a valid duration, please try again.'


class ModlogNotFound(Exception):

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs: dict[str, Any] = kwargs.copy()

    def __str__(self) -> str:
        formatted_kwargs = ', '.join(f'{key}={value}' for key, value in self.kwargs.items())
        return f'No modlogs matching the following search parameters were found: `{formatted_kwargs}`'
