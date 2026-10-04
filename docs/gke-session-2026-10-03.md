# First GKE session, 3 October 2026: dashboard history

The first full session of v2 on GKE, from the first deploy to a healthy, automatically deployed service. The screenshots show the "Weather Metrics v2" dashboard in Grafana Cloud at each stage, including a deliberate failure test and one real mistake.

All times are New Zealand time.

## Contents

1. **[Timeline](#timeline):** every event of the session in order, from creating the cluster to all panels green, including the steps that happened before the dashboard had any data.
2. **[Screenshots](#screenshots):** seven dashboard screenshots taken during the session, each with an explanation of what it shows and why.
3. **[What changed because of this session](#what-changed-because-of-this-session):** the improvements made to the project as a result.

## Timeline

| Time | Event |
|---|---|
| 09:50 | `terraform apply` creates the VPC, subnet and Autopilot cluster |
| 09:57 | Prometheus is installed and waits about 5 minutes while Autopilot creates a Spot node. The first scale-up attempt failed on the 12-vCPU quota of the project, and Autopilot retried with a smaller machine |
| 10:08–10:18 | First manual deploy, with two mistakes, both caught: a placeholder image tag, reported as `InvalidImageName`, and a placeholder API key, which kept the pod from becoming ready. A placeholder Grafana token also stopped remote write until it was replaced |
| 10:31 | First deploy by GitHub Actions through Workload Identity Federation, started by hand |
| 10:35 | First automatic deploy: a push to `main` is tested, built and deployed with no manual step |
| 10:37 | **Test:** a deploy with a broken API key. The pod never passes `/ready`, and the workflow fails after 5 minutes, as intended |
| 10:43 | The key is restored and the current commit redeployed |
| 10:44 | **Real mistake:** the image tag was mistyped, so the workflow fails, and because nothing rolls back, the app stays down |
| 10:59 | Fix: `--rollback-on-failure` is added to the deploy workflow. The push deploys automatically and restores the app |
| 11:45 | The test failures leave the one-hour window of the fetch errors panel: all panels green |

## Screenshots

### 1. One set of series per pod

![Duplicate series, one set per pod](../screenshots/history/01-duplicate-series-per-pod.jpg)

Each deploy created a new pod with a new IP address, and Prometheus labels every series with the address and node of the pod it came from. Each pod therefore produced its own series, and the "Now" panels showed one value per city for every pod in the time range.

**Fix:** the dashboard queries combine the series by city. For example, the temperature query is:

```promql
max by (location) (weatherv2_temperature_celsius{cluster="gke"})
```

The error counter uses `sum by` in the same way, so the errors from every pod are added together.

### 2. Gaps from the failed deploys

![Aggregated series with gaps from the failed deploys](../screenshots/history/02-aggregated-with-failed-deploy-gaps.png)

One line per city after the fix. The gap from 10:37 is the broken-key test. With one replica and the Recreate strategy, the working pod is stopped before the new one starts, so a deploy that never becomes ready leaves a gap in the data.

### 3. The outage from the bad image tag

![Outage from 10:44 to 11:01](../screenshots/history/03-bad-image-tag-outage.png)

From 10:44 to 11:01 there is no data: the pod could not pull the image with the mistyped tag. The workflow correctly reported the failure, but Helm did not roll back, so the app stayed down until the next successful deploy. This led to adding `--rollback-on-failure` to the deploy workflow.

### 4. Recovered after the rollback fix

![Data flowing again after the fix](../screenshots/history/04-recovered-after-rollback-fix.png)

The commit that added `--rollback-on-failure` was itself deployed automatically and brought the app back. Data flows again from 11:01. The fetch errors panel still counts the failures from the broken-key test.

### 5 and 6. Errors leaving the one-hour window

![Fetch errors falling to 2.68](../screenshots/history/05-errors-leaving-the-window.png)

![Fetch errors falling to 1.48](../screenshots/history/06-continuous-data.png)

Continuous data for all three cities. The fetch errors panel counts failures over the last hour, so the test failures count less as they move out of that window: 2.68, then 1.48. The data age panel stays between 0 and about 90 seconds: up to 60 seconds between fetches, plus up to 25 seconds until the next scrape.

### 7. All healthy: 30 minutes of normal operation

![All panels healthy over 30 minutes](../screenshots/history/07-final-healthy-30-minutes.png)

The last 30 minutes of the session, after the test failures left the one-hour window: continuous data for all three cities, data age under 90 seconds, and no fetch errors. This is what the dashboard looks like in normal operation.

## What changed because of this session

- **Automatic rollback:** the deploy workflow uses `helm upgrade --rollback-on-failure`, so a failed deploy restores the last working revision instead of leaving the app down.
- **Dashboard queries combined by city**, so redeploys do not multiply the series on the dashboard.
- **Two new panels that make problems visible:** data age, the time since the last successful fetch for each city, and fetch errors over the last hour.
- **Safer commands:** values are taken from their source instead of edited placeholders. The image tag comes from `$(git rev-parse HEAD)`, the API key from the `.env` file, and the Grafana token from a hidden `Read-Host` prompt.
