class WeatherAPIError(Exception):
    """
    Exception for:
                    The weather API could not be reached,
                    Returned an unexpected  error
    """


class LocationNotFoundError(Exception):
    """
    Exception for:
                    Passed location does not exist
    """

    def __init__(self, location: str):
        self.location = location
        super().__init__(f"Location '{location}' does not exist")
