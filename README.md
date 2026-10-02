# Weather Metrics v2

A FastAPI service that fetches weather data from the OpenWeatherMap API and exposes it as Prometheus metrics, forwarded to Grafana Cloud.

v2 runs the service on **Google Kubernetes Engine (Autopilot)**, with the infrastructure defined in **Terraform**, the app packaged with **Helm**, and deploys done by **GitHub Actions** using Workload Identity Federation (no stored keys).

v1, a Docker Compose deployment on an Oracle Cloud VPS, lives in [v-galkin/weather-metrics](https://github.com/v-galkin/weather-metrics) and is unchanged.

> Work in progress. The full README and an architecture diagram are coming.

## What changed since v1

- [The public route no longer creates metrics](docs/changes-from-v1.md#the-public-route-no-longer-creates-metrics)
- [One bad API response no longer stops the whole update](docs/changes-from-v1.md#one-bad-api-response-no-longer-stops-the-whole-update)
- [Weather data is available as soon as the app starts](docs/changes-from-v1.md#weather-data-is-available-as-soon-as-the-app-starts)
- [The fetch interval can be changed without a new build](docs/changes-from-v1.md#the-fetch-interval-can-be-changed-without-a-new-build)
- [Every dependency is pinned to an exact version](docs/changes-from-v1.md#every-dependency-is-pinned-to-an-exact-version)
- [Every image can be traced to its commit](docs/changes-from-v1.md#every-image-can-be-traced-to-its-commit)
- [The container no longer runs as root](docs/changes-from-v1.md#the-container-no-longer-runs-as-root)
- [Local runs no longer send data to the live dashboard](docs/changes-from-v1.md#local-runs-no-longer-send-data-to-the-live-dashboard)
- [A readiness check shows whether the app actually works](docs/changes-from-v1.md#a-readiness-check-shows-whether-the-app-actually-works)
- [Metrics show whether fetching is working](docs/changes-from-v1.md#metrics-show-whether-fetching-is-working)
- [An unknown city no longer stops the whole update](docs/changes-from-v1.md#an-unknown-city-no-longer-stops-the-whole-update)
- [v2 shares the Grafana Cloud stack without affecting v1](docs/changes-from-v1.md#v2-shares-the-grafana-cloud-stack-without-affecting-v1)

Each change, with the problem, the fix and the test that covers it: [docs/changes-from-v1.md](docs/changes-from-v1.md)

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
