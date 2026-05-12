# Deploying the Backend to Google Cloud Run

This guide deploys the CoachX Media AI FastAPI backend to **Cloud Run**
with **Cloud SQL for PostgreSQL** as the managed database. It assumes
you have a Google Cloud project with billing enabled and the `gcloud`
CLI installed.

The end-to-end workflow:

1. One-time GCP setup (APIs, Artifact Registry, Cloud SQL, Secret Manager).
2. Build & push the image with Cloud Build (`backend/cloudbuild.yaml`).
3. Deploy a Cloud Run service connected to Cloud SQL.
4. Run Alembic migrations against Cloud SQL.

---

## 0. Variables used in this guide

Set these once in your shell so the commands below copy-paste cleanly.

```bash
export PROJECT_ID=your-gcp-project
export REGION=asia-northeast3              # Seoul. pick any Cloud Run region
export AR_REPO=coachxmedia                  # Artifact Registry repository
export SERVICE=coachxmedia-api              # Cloud Run service name
export SQL_INSTANCE=coachxmedia-pg          # Cloud SQL instance ID
export SQL_DB=coachxmedia
export SQL_USER=coachxmedia
export SQL_INSTANCE_CONN=${PROJECT_ID}:${REGION}:${SQL_INSTANCE}

gcloud config set project "$PROJECT_ID"
```

---

## 1. Enable required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com
```

---

## 2. Create an Artifact Registry repository

```bash
gcloud artifacts repositories create "$AR_REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --description="CoachX Media AI container images"
```

---

## 3. Create a Cloud SQL Postgres instance

The smallest tier is fine for testing. Pick a strong password.

```bash
gcloud sql instances create "$SQL_INSTANCE" \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region="$REGION" \
  --storage-size=10GB \
  --storage-type=SSD

gcloud sql databases create "$SQL_DB" --instance="$SQL_INSTANCE"

gcloud sql users create "$SQL_USER" \
  --instance="$SQL_INSTANCE" \
  --password="$(openssl rand -base64 24)"
# Copy the password from the previous command's output; you'll store it
# in Secret Manager next.
```

---

## 4. Store secrets in Secret Manager

The app needs `DATABASE_URL` and `SECRET_KEY` at minimum.

```bash
# JWT signing secret
openssl rand -base64 48 | \
  gcloud secrets create coachxmedia-secret-key --data-file=-

# Database URL — uses the Cloud SQL Auth Proxy unix socket that Cloud
# Run mounts at /cloudsql/<instance-connection-name>.
# The host= query param is how asyncpg connects via the socket.
DB_PASSWORD='paste-from-step-3'
printf 'postgresql+asyncpg://%s:%s@/%s?host=/cloudsql/%s' \
  "$SQL_USER" "$DB_PASSWORD" "$SQL_DB" "$SQL_INSTANCE_CONN" | \
  gcloud secrets create coachxmedia-database-url --data-file=-
```

Grant the Cloud Run runtime service account access to both secrets:

```bash
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for SECRET in coachxmedia-secret-key coachxmedia-database-url; do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role=roles/secretmanager.secretAccessor
done
```

---

## 5. Build & push the image

From the repo root:

```bash
gcloud builds submit backend \
  --config=backend/cloudbuild.yaml \
  --substitutions=_REGION="$REGION",_AR_REPO="$AR_REPO",_SERVICE="$SERVICE",_SQL_INSTANCE="$SQL_INSTANCE_CONN"
```

The `cloudbuild.yaml` already deploys to Cloud Run as its last step,
but it does NOT wire up secrets. Set them now:

```bash
gcloud run services update "$SERVICE" \
  --region="$REGION" \
  --update-secrets=DATABASE_URL=coachxmedia-database-url:latest,SECRET_KEY=coachxmedia-secret-key:latest \
  --set-env-vars=CORS_ORIGINS='["*"]'
```

Tighten `CORS_ORIGINS` once you have a frontend URL.

---

## 6. Run database migrations

Cloud Run doesn't have a built-in "run once on deploy" step, so the
simplest path is to run Alembic from your laptop via the Cloud SQL
Auth Proxy.

```bash
# In one terminal: start the proxy
gcloud auth application-default login
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.11.0/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy
./cloud-sql-proxy "$SQL_INSTANCE_CONN"   # listens on 127.0.0.1:5432

# In another terminal: run migrations
cd backend
DATABASE_URL="postgresql+asyncpg://${SQL_USER}:${DB_PASSWORD}@127.0.0.1:5432/${SQL_DB}" \
  .venv/bin/alembic upgrade head
```

For a long-lived setup, promote this to a Cloud Run Job that runs
`alembic upgrade head` against the same Cloud SQL instance and trigger
it from Cloud Build before the deploy step.

---

## 7. Smoke-test

```bash
URL=$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')
curl "$URL/health"     # → {"status":"ok"}
open "$URL/docs"       # Swagger UI
```

---

## Re-deploying

Just re-run step 5. Cloud Build builds a new image tagged with the
commit SHA and rolls a new Cloud Run revision. Cloud Run keeps the
previous revision until the new one passes its health check.
