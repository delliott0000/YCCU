class DurationError(Exception):

    def __str__(self) -> str:
        return 'An invalid duration was specified.'
