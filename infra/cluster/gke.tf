resource "google_container_cluster" "autopilot" {
  name             = "weather-autopilot"
  location         = var.region
  enable_autopilot = true

  network    = google_compute_network.vpc.id
  subnetwork = google_compute_subnetwork.gke.id

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  release_channel {
    channel = "REGULAR"
  }

  # Required so `terraform destroy` works. Keep true for anything real.
  deletion_protection = false
}
