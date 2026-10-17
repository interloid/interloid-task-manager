import logging
from typing import BinaryIO

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from mypy_boto3_s3 import S3Client

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3StorageService:
    def __init__(self) -> None:
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            self.client: S3Client = boto3.client(
                "s3",
                region_name=settings.AWS_REGION,
                aws_access_key_id=(settings.AWS_ACCESS_KEY_ID.get_secret_value()),
                aws_secret_access_key=(
                    settings.AWS_SECRET_ACCESS_KEY.get_secret_value()
                ),
            )
        else:
            self.client = boto3.client(
                "s3",
                region_name=settings.AWS_REGION,
            )

        self.bucket_name = settings.S3_BUCKET_NAME

    def upload_file(
        self,
        file_obj: BinaryIO,
        storage_key: str,
        content_type: str,
    ) -> None:
        try:
            self.client.upload_fileobj(
                Fileobj=file_obj,
                Bucket=self.bucket_name,
                Key=storage_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "ServerSideEncryption": "AES256",
                },
            )
        except (ClientError, BotoCoreError):
            logger.exception("Failed to upload attachment to S3")
            raise

    def generate_download_url(
        self, storage_key: str, filename: str | None = None
    ) -> str:
        params = {
            "Bucket": self.bucket_name,
            "Key": storage_key,
        }
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
        try:
            return self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params=params,
                ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRE_SECONDS,
            )
        except (ClientError, BotoCoreError):
            logger.exception("Failed to generate attachment download URL")
            raise

    def delete_file(self, storage_key: str) -> None:
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=storage_key,
            )
        except (ClientError, BotoCoreError):
            logger.exception("Failed to delete attachment from S3")
            raise


s3_storage_service = S3StorageService()
