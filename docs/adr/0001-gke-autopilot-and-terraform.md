# ADR 0001: Run v2 on GKE Autopilot, managed with Terraform and Helm

## Status

Accepted, 3 October 2026. Updated the same day with lessons from the first GKE session ([session notes](../gke-session-2026-10-03.md)).

## Context

v1 runs on a single Oracle Cloud server with Docker Compose. It is deployed by GitHub Actions over SSH, using a stored SSH key, and sends its metrics to a Grafana Cloud stack with a public dashboard and alert rules.

For v2, the goals were:

- A Kubernetes-based deployment that can be created from code and destroyed on demand, so it only costs money while in use.
- No long-lived cloud credentials stored in CI.
- No risk to v1, which keeps running in production: nothing in v1's code, server, dashboard or alerts may change.
- Costs that stay within the Google Cloud free trial credit.

## Decision

**Platform: GKE Autopilot, regional, in `australia-southeast1`.**

- Autopilot instead of a Standard cluster: Google manages the nodes, and billing follows the CPU and memory the pods request. For a workload of two small pods, that is much cheaper than paying for whole machines.
- The app and Prometheus run on Spot capacity.
- Sydney is the closest region available to the project; no New Zealand region was available yet.

**Infrastructure: Terraform, in two roots with separate state.**

- `infra/bootstrap`, applied once and never destroyed: the deployer service account and the Workload Identity pool and provider.
- `infra/cluster`, applied and destroyed every session: the VPC, the subnet and the Autopilot cluster.
- State is stored in a versioned GCS bucket with public access prevented, under a separate prefix for each root.
- The roots are split because they have different lifecycles. Workload Identity pool IDs can't be reused for 30 days after deletion, so keeping them in a permanent root avoids reuse errors, and the GitHub variables that point at them stay valid.

**Packaging: Helm.**

- A custom chart for the app: one replica with the Recreate strategy, a liveness probe on `/health`, a readiness probe on `/ready`, a non-root security context, and a ClusterIP Service with Prometheus scrape annotations.
- The community Prometheus chart, pinned to version 29.35.0, with only the Prometheus server enabled and no persistent disk.

**Deployment: GitHub Actions with Workload Identity Federation.**

- The deploy workflow exchanges GitHub's short-lived OIDC token for Google credentials. The provider only accepts tokens from this repository's `main` branch.
- The deployer service account has `roles/container.developer`: it can deploy workloads but can't change or delete the cluster.
- Images are tagged with the commit SHA, and each deploy uses the SHA of the commit that CI built.
- Automatic deploys run only when the repository variable `GKE_ENABLED` is `true`, so pushes while the cluster is destroyed are skipped.
- A failed deploy rolls back automatically (`helm upgrade --rollback-on-failure`). This was added after the first GKE session, where a mistyped image tag left the app down for 17 minutes because the failed release stayed in place.

**Observability: in-cluster Prometheus, forwarding to v1's Grafana Cloud stack.**

- The plan was a separate Grafana Cloud stack for v2, but the trial allows only one stack, which v1 already uses.
- To avoid changing v1's dashboard and alerts, which query `weather_*` without any filter, Prometheus forwards only `weather_*` metrics and renames them to `weatherv2_*` as it sends them. The app itself keeps the `weather_*` names.
- v2 uses its own `metrics:write` token and its own dashboard.

**Exposure: none.** The Service is ClusterIP only; there is no load balancer or public IP.

## Consequences

- The whole environment can be rebuilt with `terraform apply`, two secrets, one Prometheus install and one deploy.
- No cloud credentials are stored in GitHub. The only stored values are repository variables that name resources and grant no access by themselves.
- The deployer can ship workloads but can't modify or delete the cluster.
- Readiness is based on the first successful fetch only, so a broken release fails the deploy, while a later OpenWeatherMap outage doesn't take the pod out of service. Problems after startup show up in the `weather_last_success_timestamp_seconds` and `weather_fetch_errors_total` metrics.
- Spot pods can be evicted. That is acceptable for this workload: the app fetches immediately on startup, so a restart costs seconds of data.
- One replica is a deliberate limit: each replica polls the API independently, so scaling out would need leader election or separating fetching from serving.
- With one replica and the Recreate strategy, the working pod is stopped before the new one starts. A deploy that never becomes ready therefore leaves a gap in the data until Helm rolls back, about 5 minutes with the current timeout.
- Each deploy creates a new pod, and Prometheus labels series with the pod's address, so every deploy starts a new set of series. Dashboard queries combine them by city (`max by (location)`, `sum by (location)`). Dropping the per-pod labels before remote write would also reduce the number of series in Grafana Cloud.
- v2 has no alert rules, because the cluster is destroyed after every session and alerts would only create noise.
- Putting a version prefix (`weatherv2_`) into metric names is not the usual practice; a label is. It was chosen only because the Grafana Cloud stack is shared with a live system. With a separate stack, both versions would keep the same names.
- Secrets (the OpenWeatherMap key and the Grafana token) are created by hand with `kubectl` each session. A managed approach, such as Secret Manager with the GKE add-on or External Secrets Operator, is a possible next step.
- Terraform is applied locally. CI checks formatting and syntax on pull requests but does not run `terraform plan`, which would need read access to the project and the state bucket.

## Alternatives considered

- **GKE Standard:** more control over nodes, but you pay for whole nodes even when idle, and you manage node pools yourself.
- **Cloud Run:** simpler and cheaper for a web service, but the app runs a background scheduler that needs to stay running, and the goal was to use Kubernetes, Helm and Prometheus.
- **A service account JSON key stored in GitHub:** simpler to set up, but a long-lived secret that can leak and has to be rotated by hand.
- **A second Grafana Cloud account:** full isolation from v1 without renaming metrics, at the cost of a separate login. Not chosen, to keep a single account.
