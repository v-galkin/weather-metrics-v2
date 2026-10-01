variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "github_repository" {
  description = "owner/repo allowed to deploy, e.g. v-galkin/weather-metrics-v2"
  type        = string
}