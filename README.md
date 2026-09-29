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

### The fetch interval can be changed without a new build

**Problem:** in v1, the 60-second fetch interval was hard-coded in a dictionary in `app/weather/scheduler.py`:

```python
scheduler_config = {
    "query_interval": 60,
}
```

- **Changing it needed a new release.** Edit the code, commit, build a new image and redeploy, just to change one number.
- **Inconsistent with other settings.** The API key, URL, timeout and locations were already in `app/core/config.py` and could be changed with environment variables; the interval wasn't.
- **No validation.** Nothing stopped a value of `0` or a negative number.

**Change:** the interval is now a setting, `fetch_interval_seconds` in `app/core/config.py`, with a default of 60. It can be changed with the `FETCH_INTERVAL_SECONDS` environment variable (on GKE, from the Helm chart's values). It must be greater than 0: an invalid value stops the app at startup with a clear error instead of letting it run with a broken schedule.

All settings can now be set with environment variables, including the locations, as JSON: `LOCATIONS='["London", "Paris"]'`.

**Test:** two tests in `tests/test_scheduler.py`, both written before the fix and failing against the v1 code:
- `test_start_scheduler_uses_interval_from_settings` sets `FETCH_INTERVAL_SECONDS=30` and checks that the scheduler's job runs every 30 seconds.
- `test_settings_rejects_non_positive_interval` sets it to `0` and checks that the settings are rejected.

### Every dependency is pinned to an exact version

**Problem:** in v1, `requirements.txt` listed package names without versions, so every install got whatever was newest that day:

```
Laptop (last month)   → fastapi 0.135, ruff 0.12
CI run (today)        → fastapi 0.142, ruff 0.16   ← different
Docker build (later)  → fastapi 0.150, ruff 0.18   ← different again
```

- **The same code could build a different image.** Redeploying an old commit could install newer, untested versions.
- **Surprise breakages.** While building v2, a newer ruff started failing code that had passed in v1 (new `DTZ005` and `I001` rules), and a newer Starlette started showing a deprecation warning, without any change to the code.
- **Hidden dependencies weren't controlled.** The packages the app's own dependencies install (for example Starlette and anyio, installed by FastAPI) could change at any time.
- **Unused packages.** `requirements-dev.txt` included `requests`, which nothing used, and listed `python-dotenv` twice.

**Change:** dependencies are now managed with [pip-tools](https://github.com/jazzband/pip-tools):

| File | Written by | Contains |
|---|---|---|
| `requirements.in` | Hand | The packages the app uses directly |
| `requirements.txt` | `pip-compile` | Every package the app needs, each pinned to an exact version |
| `requirements-dev.in` | Hand | Test and lint tools, plus the app's packages at the same versions |
| `requirements-dev.txt` | `pip-compile` | Every development package, pinned |

The Docker image and CI install from the generated `.txt` files, so a laptop, CI and every build use exactly the same versions. `requests` and the duplicate `python-dotenv` were removed.

Updating is now a deliberate step that shows up as a reviewable commit:

```
pip-compile --upgrade requirements.in
pip-compile --upgrade requirements-dev.in
pip-sync requirements-dev.txt
pytest
```

**Test:** no new test. The full test suite passes after `pip-sync` installs exactly the pinned versions and removes everything else, which also confirms that nothing needed `requests`.

### The container no longer runs as root

**Problem:** in v1, the Dockerfile had no `USER` instruction, so the app ran as root inside the container:

```
docker run --rm <v1 image> id   → uid=0(root)
```

- **A bigger impact from any security hole.** If a flaw in the app or one of its dependencies let someone run code, that code would run as root, making it easier to tamper with the container or try to escape from it.
- **Blocked by Kubernetes security settings.** Clusters that require containers to run as non-root (`runAsNonRoot: true`) refuse to start a root container, and security scanners flag it.

**Change:** the Dockerfile creates an unprivileged user, `appuser` (UID 10001), with no home folder and no login shell, and switches to it with `USER 10001` after the packages are installed:

- **Installing still runs as root,** because `pip install` needs to write to the system Python folders. Only the running app is non-root.
- **The app can't change its own code.** The application files are owned by root, so the app user can read them but not modify them.
- **A numeric UID** (`USER 10001` rather than `USER appuser`) lets Kubernetes check that the user isn't root before starting the pod. With a name, it can't check, and it refuses to start the pod.

```
docker run --rm <v2 image> id   → uid=10001(appuser)
```

**Test:** no automated test. Checked by building the image, confirming with `id` that it runs as UID 10001, and confirming the app still serves `/health` and `/metrics` as that user.

### Local runs no longer send data to the live dashboard

**Problem:** in v1, one `prometheus.yml` was used both in production and for local development, and it always sent every metric to Grafana Cloud:

```
Laptop:  docker compose -f docker-compose-dev.yml up
         → local Prometheus → remote_write → the live v1 Grafana Cloud stack
```

- **Test data mixed with production data.** Local runs used the same `job="weather-service"` label, so the live dashboard showed them alongside the real data, and they could affect the alerts.
- **A production secret was needed to develop locally.** The dev setup mounted the Grafana Cloud token file; without it, Prometheus failed to start.

**Change:** in v2, `prometheus.yml` is for local development only. It scrapes the app and sends nothing anywhere, and the dev Docker Compose file no longer mounts a token. On GKE, Prometheus is configured separately by its Helm chart and sends data to its own Grafana Cloud stack. The Prometheus image is also pinned to a specific version instead of `latest`.

**Test:** no automated test. Checked by running the dev Docker Compose setup with no token file: the `weather-service` target shows as up in the Prometheus UI, the query `weather_temperature_celsius` returns the three cities, and the logs show no remote_write activity.

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
