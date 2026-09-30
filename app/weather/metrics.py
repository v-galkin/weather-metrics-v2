from prometheus_client import Counter, Gauge

temperature_celsius = Gauge(
    "weather_temperature_celsius", "Current Temperature in Celsius", ["location"]
)

humidity_percent = Gauge(
    "weather_humidity_percent", "Current humidity percentage", ["location"]
)

wind_speed_mps = Gauge(
    "weather_wind_speed_mps", "Current wind speed in metres per second", ["location"]
)

last_success_timestamp = Gauge(
    "weather_last_success_timestamp_seconds",
    "Unix time of the last successful fetch",
    ["location"],
)

fetch_errors = Counter("weather_fetch_errors", "Number of failed fetches", ["location"])


def record_fetch_error(location: str) -> None:
    fetch_errors.labels(location=location).inc()


def update_metrics(reading: dict) -> None:
    temperature_celsius.labels(location=reading["location"]).set(
        reading["temperature_c"]
    )

    humidity_percent.labels(location=reading["location"]).set(
        reading["humidity_percent"]
    )

    wind_speed_mps.labels(location=reading["location"]).set(reading["wind_speed_mps"])

    last_success_timestamp.labels(location=reading["location"]).set_to_current_time()
