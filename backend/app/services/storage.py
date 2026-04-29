import io
import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.config import settings

LOCAL_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "local_uploads")


class S3StorageService:
    def __init__(self):
        kwargs = {
            "region_name": settings.AWS_REGION,
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        }
        if settings.S3_ENDPOINT_URL:
            kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
        self.client = boto3.client("s3", **kwargs)
        self.bucket = settings.S3_BUCKET

    def upload_file(self, file_obj: io.IOBase, key: str, content_type: str) -> str:
        self.client.upload_fileobj(
            file_obj,
            self.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return f"s3://{self.bucket}/{key}"

    def generate_presigned_put_url(
        self, key: str, content_type: str, expires: int = 3600
    ) -> str:
        return self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires,
        )

    def generate_presigned_get_url(self, key: str, expires: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires,
        )

    def delete_file(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError:
            pass


class LocalFileStorageService:
    """Filesystem fallback for development without AWS credentials."""

    def __init__(self):
        os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)

    def _local_path(self, key: str) -> str:
        safe_key = key.replace("/", os.sep)
        return os.path.join(LOCAL_STORAGE_DIR, safe_key)

    def upload_file(self, file_obj: io.IOBase, key: str, content_type: str) -> str:
        local_path = self._local_path(key)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(file_obj.read())
        return f"local://{key}"

    def generate_presigned_put_url(
        self, key: str, content_type: str, expires: int = 3600
    ) -> str:
        # Return a stub URL for local dev
        return f"http://localhost:8000/dev-upload/{key}"

    def generate_presigned_get_url(self, key: str, expires: int = 3600) -> str:
        return f"http://localhost:8000/dev-download/{key}"

    def delete_file(self, key: str) -> None:
        local_path = self._local_path(key)
        if os.path.exists(local_path):
            os.remove(local_path)


def get_storage_service() -> S3StorageService | LocalFileStorageService:
    if settings.AWS_ACCESS_KEY_ID:
        return S3StorageService()
    return LocalFileStorageService()
