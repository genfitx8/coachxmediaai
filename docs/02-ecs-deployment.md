# 02 — ECS Fargate Deployment

This document describes how the CoachX Media AI backend is deployed on AWS ECS Fargate.

---

## Architecture

```
Internet
   │
   ▼
Application Load Balancer (HTTPS :443)
   │
   ▼
ECS Fargate Cluster
   ├── coachxmedia-api   (FastAPI, uvicorn)
   └── coachxmedia-worker (Celery)
         │
         ├── RDS PostgreSQL 15
         ├── ElastiCache Redis 7
         └── S3 (media storage)
```

---

## Task Definitions

### API Task (`coachxmedia-api`)

| Setting | Value |
|---|---|
| CPU | 512 |
| Memory | 1024 MiB |
| Port | 8000 |
| Command | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2` |

### Worker Task (`coachxmedia-worker`)

| Setting | Value |
|---|---|
| CPU | 1024 |
| Memory | 2048 MiB |
| Command | `celery -A app.workers.celery_app worker --loglevel=info --concurrency=4` |

---

## Health Check

The API exposes a `/health` endpoint that returns `{"status": "ok"}`.  
Configure the ALB target group to use this path for health checks.

---

## Scaling

Configure ECS Application Auto Scaling on the `coachxmedia-api` service:
- Scale out when CPU > 70% for 2 consecutive periods
- Scale in when CPU < 30% for 5 consecutive periods
- Min tasks: 1, Max tasks: 10

For the Celery worker, scale based on the Redis queue length using a custom CloudWatch metric.

---

## Logging

Both tasks ship logs to CloudWatch Logs:
- `/coachxmedia/api`
- `/coachxmedia/worker`

Retention is set to 30 days by default.
