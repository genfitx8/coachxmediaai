output "api_url" {
  description = "Public URL of the FastAPI service (ALB DNS name)"
  value       = "https://<alb-dns-name>"  # Replace once ALB is configured
}

output "s3_bucket_name" {
  description = "Name of the S3 media upload bucket"
  value       = "${var.app_name}-uploads-${var.environment}"
}
