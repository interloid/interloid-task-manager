from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.responses import (
    NOT_FOUND_RESPONSE,
    PAYLOAD_TOO_LARGE_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    UNSUPPORTED_MEDIA_TYPE_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
)
from app.core.config import settings
from app.db.dependencies import get_db
from app.models.user import User
from app.repositories import TaskAttachmentRepository, TaskRepository
from app.schemas import (
    APIResponse,
    MessageResponse,
    TaskAttachmentResponse,
)
from app.schemas.task_attachment import AttachmentDownloadResponse
from app.services.s3_storage_service import s3_storage_service
from app.services.task_attachment_service import TaskAttachmentService

router = APIRouter(
    prefix="/tasks",
    tags=["Task Attachments"],
)


def get_attachment_service(
    db: AsyncSession,
) -> TaskAttachmentService:
    return TaskAttachmentService(
        task_repository=TaskRepository(db),
        attachment_repository=TaskAttachmentRepository(db),
        storage_service=s3_storage_service,
    )


@router.post(
    "/{task_id}/attachments",
    response_model=APIResponse[TaskAttachmentResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
        **PAYLOAD_TOO_LARGE_RESPONSE,
        **UNSUPPORTED_MEDIA_TYPE_RESPONSE,
    },
)
async def upload_task_attachment(
    task_id: UUID,
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[
        AsyncSession,
        Depends(get_db, scope="function"),
    ],
) -> APIResponse[TaskAttachmentResponse]:
    service = get_attachment_service(db)

    attachment = await service.upload_attachment(
        task_id=task_id,
        current_user=current_user,
        upload=file,
    )

    return APIResponse(
        message="Attachment uploaded successfully",
        data=attachment,
    )


@router.get(
    "/{task_id}/attachments",
    response_model=APIResponse[list[TaskAttachmentResponse]],
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **NOT_FOUND_RESPONSE,
    },
)
async def list_task_attachments(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[
        AsyncSession,
        Depends(get_db, scope="function"),
    ],
) -> APIResponse[list[TaskAttachmentResponse]]:
    service = get_attachment_service(db)

    attachments = await service.list_attachments(
        task_id=task_id,
        current_user=current_user,
    )

    return APIResponse(
        message="Attachments retrieved successfully",
        data=attachments,
    )


@router.get(
    "/{task_id}/attachments/{attachment_id}",
    response_model=APIResponse[TaskAttachmentResponse],
    responses={
        **UNAUTHORIZED_RESPONSE,
        **NOT_FOUND_RESPONSE,
    },
)
async def get_task_attachment(
    task_id: UUID,
    attachment_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[
        AsyncSession,
        Depends(get_db, scope="function"),
    ],
) -> APIResponse[TaskAttachmentResponse]:
    service = get_attachment_service(db)

    attachment = await service.get_attachment_details(
        task_id=task_id,
        attachment_id=attachment_id,
        current_user=current_user,
    )

    return APIResponse(
        message="Attachment retrieved successfully",
        data=attachment,
    )


@router.get(
    "/{task_id}/attachments/{attachment_id}/download",
    response_model=APIResponse[AttachmentDownloadResponse],
    responses={
        **UNAUTHORIZED_RESPONSE,
        **NOT_FOUND_RESPONSE,
    },
)
async def download_task_attachment(
    task_id: UUID,
    attachment_id: UUID,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Annotated[
        AsyncSession,
        Depends(get_db, scope="function"),
    ],
) -> APIResponse[AttachmentDownloadResponse]:
    service = get_attachment_service(db)

    download_url = await service.get_download_url(
        task_id=task_id,
        attachment_id=attachment_id,
        current_user=current_user,
    )

    return APIResponse(
        message="Download URL generated successfully",
        data=AttachmentDownloadResponse(
            download_url=download_url,
            expires_in=settings.S3_PRESIGNED_URL_EXPIRE_SECONDS,
        ),
    )


@router.delete(
    "/{task_id}/attachments/{attachment_id}",
    response_model=MessageResponse,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **NOT_FOUND_RESPONSE,
    },
)
async def delete_task_attachment(
    task_id: UUID,
    attachment_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> MessageResponse:
    service = get_attachment_service(db)

    await service.delete_attachment(
        task_id=task_id,
        attachment_id=attachment_id,
        current_user=current_user,
    )

    return MessageResponse(message="Attachment deleted successfully")
