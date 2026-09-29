# Weather Metrics v2

A FastAPI service that fetches weather data from the OpenWeatherMap API and exposes it as Prometheus metrics, forwarded to Grafana Cloud.

v2 runs the service on **Google Kubernetes Engine (Autopilot)**, with the infrastructure defined in **Terraform**, the app packaged with **Helm**, and deploys done by **GitHub Actions** using Workload Identity Federation (no stored keys).

v1, a Docker Compose deployment on an Oracle Cloud VPS, lives in [v-galkin/weather-metrics](https://github.com/v-galkin/weather-metrics) and is unchanged.

> Work in progress. The full README, architecture diagram and a "What changed since v1" section are coming.

## What changed since v1

### The public route no longer creates metrics

**Problem:** in v1, every request to `/weather/{location}` added the requested city to the Prometheus metrics, even if it wasn't one of the configured cities:

```
/weather/Paris   → weather_temperature_celsius{location="Paris"}
/weather/paris   → weather_temperature_celsius{location="paris"}   ← a separate series
/weather/PARIS   → weather_temperature_celsius{location="PARIS"}   ← another one
```

- **Anyone controlled the metrics.** The route is public, so any visitor could add cities to the dashboard.
- **One city, many series.** Prometheus treats every spelling as a different city, so the same place could appear several times.
- **The series never went away.** Each one stayed in the metrics until the app restarted.
- **The values went stale.** The scheduler never fetched these cities again, so they kept showing the value from the one request that created them.
- **Higher cost.** Every series counts towards the Grafana Cloud free-tier limit, so a script trying many city names could push the account over it.

**Change:** the route (`app/routers/weather.py`) now only fetches the weather and returns it. The `update_metrics` call was removed from it. Only the scheduler updates metrics, and only for the cities configured in `app/core/config.py`.

**Test:** `test_get_weather_does_not_update_metrics` in `tests/test_routes.py` calls the route with a mocked weather API, then checks that no metric series was created for that city. It was written before the fix, failed against the v1 code, and passes now, so the bug can't come back unnoticed.

### One bad API response no longer stops the whole update

**Problem:** in v1, the app assumed that a successful (200) response from OpenWeatherMap always contained valid data. When it didn't, parsing raised an error the rest of the app wasn't expecting:

```
200 with {"wind": {...}} (no "main")   → KeyError: 'main'
200 with {"main": null, ...}           → TypeError
200 with "<html>Bad gateway</html>"    → JSONDecodeError
```

- **Other cities were skipped.** The scheduler only handled `WeatherAPIError`. A bad response for London stopped the update round, so Auckland and New York weren't updated either.
- **The wrong error code.** The `/weather/{location}` route returned a 500 ("our server is broken") instead of a 502 ("the weather API failed").

**Change:** `weather()` in `app/weather/fetch.py` now catches these parsing errors and raises `WeatherAPIError` instead, keeping the original error attached for the logs. The scheduler and the route already handle `WeatherAPIError`: the scheduler skips that city and carries on with the others, and the route returns a 502.

**Test:** `test_weather_missing_fields` and `test_weather_invalid_json` in `tests/test_fetch.py` mock a 200 response with a missing field and with a body that isn't JSON, and check that `WeatherAPIError` is raised. Both were written before the fix and failed against the v1 code.

### Weather data is available as soon as the app starts

**Problem:** in v1, the first weather fetch happened only one full interval (60 seconds) after the app started:

```
0 s    app starts        → /metrics has no weather data
60 s   first fetch runs  → London, Auckland and New York appear
```

- **A gap after every start.** For the first minute, the dashboard had nothing new to show.
- **Frequent on Kubernetes.** On GKE, the pod restarts on every deploy and whenever a Spot node is reclaimed, so this gap happens far more often than on the v1 server.
- **Hidden side effect.** The job was added to the scheduler when the module was imported, not when the app started, so simply importing the module (as the tests do) registered it.

**Change:** a new `start_scheduler()` function in `app/weather/scheduler.py` adds the job and starts the scheduler, and the app calls it on startup (`app/main.py`). The job's first run is set to "now" (`next_run_time`, in UTC so it doesn't depend on the server's timezone), then it repeats every 60 seconds. The job also has a fixed ID, so starting the scheduler twice can't create a duplicate job that fetches every city twice.

**Test:** `test_start_scheduler_runs_first_update_immediately` in `tests/test_scheduler.py` starts the scheduler with the fetch mocked out, and checks that the first run is due within a few seconds, not a minute later. It was written before the fix and failed against the v1 code.

## Running locally

Create a `.env` file in the project root with your own [OpenWeatherMap API key](https://openweathermap.org/api):

```
OPENWEATHER_API_KEY=your_key_here
```

1. **Create a virtual environment**
   ```
   python -m venv venv
   ```

2. **Activate it**

   Windows (PowerShell):
   ```
   venv\Scripts\Activate.ps1
   ```
   If PowerShell says running scripts is disabled, allow local scripts once, then activate again:
   ```
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```

   macOS / Linux:
   ```
   source venv/bin/activate
   ```

   The prompt starts with `(venv)` while the environment is active. Run `deactivate` to leave it.

3. **Install the dependencies**
   ```
   pip install -r requirements-dev.txt
   ```

4. **Run the application** (at `http://localhost:8000`)
   ```
   uvicorn app.main:app --reload
   ```

5. **Run the tests and linters**
   ```
   pytest -v
   ruff check .
   black --check .
   ```
