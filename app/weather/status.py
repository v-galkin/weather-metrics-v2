class FetchStatus:
    """Tracks whether the scheduler has completed a successful fetch."""

    def __init__(self) -> None:
        self.has_fetched = False

    def mark_success(self) -> None:
        self.has_fetched = True

    def is_ready(self) -> bool:
        return self.has_fetched


fetch_status = FetchStatus()
