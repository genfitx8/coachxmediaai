# 01 — AWS Quick-Start Deployment Guide

This guide walks through the minimum steps to deploy CoachX Media AI to AWS for the first time.

---

## Prerequisites

- AWS account with admin or power-user permissions
- AWS CLI v2 configured (`aws configure`)
- Docker installed locally
- Terraform ≥ 1.6 (see `infra/terraform/`)

---

## Step 1 — Push Docker Images to ECR

```bash
# Create ECR repositories (once)
aws ecr create-repository --repository-name coachxmedia-api
aws ecr create-repository --repository-name coachxmedia-worker

# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin \
    <account_id>.dkr.ecr.us-east-1.amazonaws.com

# Build and push the API image
cd backend
docker build -t coachxmedia-api .
docker tag coachxmedia-api <account_id>.dkr.ecr.us-east-1.amazonaws.com/coachxmedia-api:latest
docker push <account_id>.dkr.ecr.us-east-1.amazonaws.com/coachxmedia-api:latest

# Build and push the worker image
docker build -f Dockerfile.worker -t coachxmedia-worker .
docker tag coachxmedia-worker <account_id>.dkr.ecr.us-east-1.amazonaws.com/coachxmedia-worker:latest
docker push <account_id>.dkr.ecr.us-east-1.amazonaws.com/coachxmedia-worker:latest
```

---

## Step 2 — Provision Infrastructure with Terraform

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

terraform init
terraform plan
terraform apply
```

---

## Step 3 — Run Database Migrations

Once the ECS task is running:

```bash
aws ecs run-task \
  --cluster coachxmedia \
  --task-definition coachxmedia-api \
  --overrides '{"containerOverrides":[{"name":"api","command":["alembic","upgrade","head"]}]}' \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

---

## Step 4 — Configure DNS

Point your domain to the ALB DNS name output by Terraform (`api_url`).  
If using CloudFront, update the CNAME accordingly.

---

## Step 5 — Set Up Stripe Webhooks

1. In the [Stripe Dashboard](https://dashboard.stripe.com/webhooks), add a new endpoint:  
   `https://api.yourdomain.com/api/v1/payments/webhook`
2. Select events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
3. Copy the signing secret into your ECS task environment variable `STRIPE_WEBHOOK_SECRET`.

---

## Environment Variables for Production

Store secrets in AWS Systems Manager Parameter Store under `/coachxmedia/`:

```bash
aws ssm put-parameter --name /coachxmedia/SECRET_KEY --type SecureString --value "..."
aws ssm put-parameter --name /coachxmedia/DATABASE_URL --type SecureString --value "..."
aws ssm put-parameter --name /coachxmedia/STRIPE_SECRET_KEY --type SecureString --value "..."
aws ssm put-parameter --name /coachxmedia/STRIPE_WEBHOOK_SECRET --type SecureString --value "..."
```

The ECS task role (see `infra/policies/ecs-task-role.json`) grants read access to these parameters.
