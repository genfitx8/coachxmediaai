# CoachX Media AI — Infrastructure

This directory contains infrastructure-as-code (Terraform) and AWS IAM/S3 policy documents for deploying CoachX Media AI to AWS.

---

## Directory Layout

```
infra/
├── terraform/          # Terraform modules (ECS, RDS, ElastiCache, CloudFront, S3)
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── modules/
│       ├── ecs/
│       ├── rds/
│       ├── elasticache/
│       ├── s3/
│       └── cloudfront/
└── policies/           # IAM and S3 bucket policies
    ├── ecs-task-role.json
    └── s3-upload-policy.json
```

---

## Prerequisites

- [Terraform ≥ 1.6](https://developer.hashicorp.com/terraform/install)
- AWS CLI configured with appropriate permissions
- An S3 bucket for Terraform remote state (update `backend` block in `main.tf`)

---

## Quick Start

```bash
cd infra/terraform
terraform init
terraform plan -var-file=prod.tfvars
terraform apply -var-file=prod.tfvars
```

---

## Key Resources Managed

| Resource | Description |
|---|---|
| ECS Fargate | Runs the FastAPI API container and Celery worker |
| RDS PostgreSQL | Managed PostgreSQL 15 database |
| ElastiCache Redis | Redis 7 for Celery broker and result backend |
| S3 | Media upload storage |
| CloudFront | CDN in front of S3 and optionally the frontend |
| ACM | TLS certificates for custom domains |
| ALB | Application Load Balancer for ECS services |

See the Terraform module directories for individual resource configurations.
