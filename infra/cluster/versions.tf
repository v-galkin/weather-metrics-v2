terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.0"
    }
  }

  # Backend blocks can't use variables, so the bucket name is written out
  backend "gcs" {
    bucket = "weather-metrics-v2-tfstate-2026"
    prefix = "cluster"
  }
}
