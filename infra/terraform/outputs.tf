output "api_url" {
  description = "Public URL of the FastAPI service (ALB DNS name). Update once the ALB resource (e.g. aws_lb.api.dns_name) is configured in this module."
  value       = "https://<configure aws_lb.api.dns_name here>"
}

output "s3_bucket_name" {
  description = "Name of the S3 media upload bucket"
  value       = "${var.app_name}-uploads-${var.environment}"
}
