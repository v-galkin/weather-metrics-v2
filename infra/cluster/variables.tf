variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Region for the network and the cluster"
  type        = string
  default     = "australia-southeast1"
}
