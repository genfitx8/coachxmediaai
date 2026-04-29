import uuid
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.workers.celery_app import celery_app
from app.services.ai_processor import transcribe, summarize, analyze

# Sync engine for Celery workers (Celery does not support async I/O natively)
_sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace(
    "postgresql+asyncpg", "postgresql+psycopg2"
)
sync_engine = create_engine(_sync_url)
SyncSession = sessionmaker(bind=sync_engine)


@celery_app.task(bind=True, name="app.workers.tasks.process_ai_job")
def process_ai_job(self, job_id: str):
    from app.models.job import AIJob
    from app.models.media import Media

    with SyncSession() as db:
        job = db.query(AIJob).filter(AIJob.id == uuid.UUID(job_id)).first()
        if not job:
            return

        job.status = "running"
        job.celery_task_id = self.request.id
        db.commit()

        try:
            media_key = None
            if job.media_id:
                media = db.query(Media).filter(Media.id == job.media_id).first()
                if media:
                    media_key = media.storage_key

            if job.job_type == "transcription":
                result = transcribe(media_key or "")
            elif job.job_type == "summary":
                transcript = (job.result or {}).get("transcript", "") if job.result else ""
                result = summarize(transcript)
            elif job.job_type == "analysis":
                result = analyze(media_key or "")
            else:
                raise ValueError(f"Unknown job_type: {job.job_type}")

            job.result = result
            job.status = "completed"

        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)

        finally:
            db.commit()
