import logging
from uuid import UUID, uuid4

from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from app.core.config import settings
from app.enums import RoleName
from app.exceptions.task import TaskNotFoundException
from app.exceptions.task_attachment import (
    AttachmentNotFoundException,
    AttachmentTooLargeException,
    InvalidAttachmentException,
    UnsupportedAttachmentTypeException,
)
from app.models.task_attachment import TaskAttachment
from app.models.user import User
from app.repositories import TaskAttachmentRepository, TaskRepository
from app.services.s3_storage_service import S3StorageService

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain",
}


class TaskAttachmentService:
    def __init__(
        self,
        task_repository: TaskRepository,
        attachment_repository: TaskAttachmentRepository,
        storage_service: S3StorageService,
    ) -> None:
        self.task_repository = task_repository
        self.attachment_repository = attachment_repository
        self.storage_service = storage_service

    async def upload_attachment(
        self,
        *,
        task_id: UUID,
        current_user: User,
        upload: UploadFile,
    ) -> TaskAttachment:

        task = await self.task_repository.get_by_id(task_id)

        if task is None:
            raise TaskNotFoundException()

        if current_user.role != RoleName.ADMIN and task.owner_id != current_user.id:
            raise TaskNotFoundException()

        filename = upload.filename

        if not filename or not filename.strip():
            raise InvalidAttachmentException(
                message="A filename is required",
                code="INVALID_FILENAME",
            )

        if len(filename) > 255:
            raise InvalidAttachmentException(
                message="Filename must not exceed 255 characters",
                code="INVALID_FILENAME",
            )

        content_type = upload.content_type or ""

        if content_type not in ALLOWED_CONTENT_TYPES:
            raise UnsupportedAttachmentTypeException()

        upload.file.seek(0, 2)
        file_size = upload.file.tell()
        upload.file.seek(0)

        if file_size == 0:
            raise InvalidAttachmentException(
                message="Empty files are not allowed",
                code="EMPTY_FILE",
            )

        if file_size > settings.TASK_ATTACHMENT_MAX_SIZE_BYTES:
            raise AttachmentTooLargeException()

        storage_key = f"tasks/{task_id}/{uuid4().hex}"

        await run_in_threadpool(
            self.storage_service.upload_file,
            upload.file,
            storage_key,
            content_type,
        )

        attachment = TaskAttachment(
            task_id=task_id,
            uploaded_by_id=current_user.id,
            original_filename=filename,
            storage_key=storage_key,
            content_type=content_type,
            file_size=file_size,
        )

        try:
            return await self.attachment_repository.create(attachment)
        except Exception:
            logger.exception(
                "Failed to save attachment metadata; cleaning up S3 object"
            )

            try:
                await run_in_threadpool(
                    self.storage_service.delete_file,
                    storage_key,
                )
            except Exception:
                logger.exception("Failed to clean up S3 object after database failure")

            raise

    async def list_attachments(
        self,
        *,
        task_id: UUID,
        current_user: User,
    ) -> list[TaskAttachment]:

        task = await self.task_repository.get_by_id(task_id)

        if task is None:
            raise TaskNotFoundException()

        if current_user.role != RoleName.ADMIN and task.owner_id != current_user.id:
            raise TaskNotFoundException()

        return await self.attachment_repository.get_by_task(task_id)

    async def get_attachment_details(
        self, *, task_id: UUID, attachment_id: UUID, current_user: User
    ) -> TaskAttachment:
        task = await self.task_repository.get_by_id(task_id)

        if task is None:
            raise TaskNotFoundException()

        if current_user.role != RoleName.ADMIN and task.owner_id != current_user.id:
            raise TaskNotFoundException()

        attachment = await self.attachment_repository.get_by_id_and_task(
            attachment_id=attachment_id,
            task_id=task_id,
        )

        if attachment is None:
            raise AttachmentNotFoundException()

        return attachment

    async def get_download_url(
        self,
        *,
        task_id: UUID,
        attachment_id: UUID,
        current_user: User,
    ) -> str:

        task = await self.task_repository.get_by_id(task_id)

        if task is None:
            raise TaskNotFoundException()

        if current_user.role != RoleName.ADMIN and task.owner_id != current_user.id:
            raise TaskNotFoundException()

        attachment = await self.attachment_repository.get_by_id_and_task(
            task_id=task_id,
            attachment_id=attachment_id,
        )

        if attachment is None:
            raise TaskNotFoundException()

        return await run_in_threadpool(
            self.storage_service.generate_download_url,
            attachment.storage_key,
        )

    async def delete_attachment(
        self,
        *,
        task_id: UUID,
        attachment_id: UUID,
        current_user: User,
    ) -> None:
        task = await self.task_repository.get_by_id(task_id)

        if task is None:
            raise TaskNotFoundException()

        if current_user.role != RoleName.ADMIN and task.owner_id != current_user.id:
            raise TaskNotFoundException()

        attachment = await self.attachment_repository.get_by_id_and_task(
            task_id=task_id, attachment_id=attachment_id
        )

        if attachment is None:
            raise AttachmentNotFoundException()

        await run_in_threadpool(
            self.storage_service.delete_file,
            attachment.storage_key,
        )

        await self.attachment_repository.delete(attachment)
