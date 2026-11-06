class UserbotDispatcherState:
    """Update types the userbot dispatcher accepts, resolved once at startup.

    The master bot runs on its own dispatcher, so its update types are
    passed to the webhook call explicitly and are never stored here.
    """

    def __init__(self):
        self._allowed_updates: list[str] | None = None

    @property
    def allowed_updates(self) -> list[str]:
        if self._allowed_updates is None:
            raise RuntimeError("Userbot dispatcher allowed_updates is not resolved yet")
        return self._allowed_updates

    @allowed_updates.setter
    def allowed_updates(self, value: list[str]) -> None:
        if not isinstance(value, list):
            raise ValueError("allowed updates should be list.")
        self._allowed_updates = value
