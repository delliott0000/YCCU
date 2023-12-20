class DurationError(Exception):

    def __init__(self, duration: str, /) -> None:
        self.duration: str = duration

    def __str__(self) -> str:
        return f'`{self.duration}` is not a valid duration, please try again.'
