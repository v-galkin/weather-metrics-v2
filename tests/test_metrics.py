import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.main import app
from app.weather.metrics import update_metrics

client = TestClient(app)


# Helpers
@pytest.fixture
def _test_metrics() -> dict:
    return {
        "location": "Metrics_Loc_A",
        "temp": 14.2,
        "humidity": 81,
        "wind_speed": 4.1,
    }


def _seed_metrics(metrics: dict) -> None:
    update_metrics(
        {
            "location": metrics["location"],
            "temperature_c": metrics["temp"],
            "humidity_percent": metrics["humidity"],
            "wind_speed_mps": metrics["wind_speed"],
        }
    )


# ------------------------------------------------------------------------------------


# Actual Tests
def test_update_metrics_sets_gauge_values(_test_metrics):
    _seed_metrics(_test_metrics)

    assert (
        REGISTRY.get_sample_value(
            "weather_temperature_celsius", {"location": _test_metrics["location"]}
        )
        == _test_metrics["temp"]
    )

    assert (
        REGISTRY.get_sample_value(
            "weather_humidity_percent", {"location": _test_metrics["location"]}
        )
        == _test_metrics["humidity"]
    )

    assert (
        REGISTRY.get_sample_value(
            "weather_wind_speed_mps", {"location": _test_metrics["location"]}
        )
        == _test_metrics["wind_speed"]
    )


def test_metrics_endpoint_returns_prometheus_format(_test_metrics):
    _seed_metrics(_test_metrics)

    response = client.get("/metrics")

    expected_data = f'weather_temperature_celsius{{location="{_test_metrics["location"]}"}} {_test_metrics["temp"]}'

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert expected_data in response.text
