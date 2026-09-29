from prometheus_client import Gauge

temperature_celsius = Gauge(
    "weather_temperature_celsius", "Current Temperature in Celsius", ["location"]
)

humidity_percent = Gauge(
    "weather_humidity_percent", "Current humidity percentage", ["location"]
)

wind_speed_mps = Gauge(
    "weather_wind_speed_mps", "Current wind speed in metres per second", ["location"]
)


def update_metrics(reading: dict) -> None:
    temperature_celsius.labels(location=reading["location"]).set(
        reading["temperature_c"]
    )
    humidity_percent.labels(location=reading["location"]).set(
        reading["humidity_percent"]
    )
    wind_speed_mps.labels(location=reading["location"]).set(reading["wind_speed_mps"])
