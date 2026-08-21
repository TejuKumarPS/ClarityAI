import logging
import uuid
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status

from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.input_handlers.factory import InputHandlerFactory
from app.input_handlers.exceptions import (
    TranscriptInputError,
    UnsupportedInputTypeError,
    EmptyTranscriptError,
    TranscriptTooShortError,
    InvalidFileFormatError,
    TranscriptExtractionError,
    FileSizeLimitExceededError,
)
from app.models.user import User
from app.models.job import Job
from app.schemas.job import JobResponse
from app.worker.tasks import process_job

logger = logging.getLogger(__name__)
router = APIRouter()



@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new transcript processing job",
)
async def create_job(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content_type = request.headers.get("content-type", "").lower()

    input_type: str = ""
    raw_content: Any = None
    filename: Optional[str] = None

    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed JSON in request body",
            )

        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=422,
                detail="Expected a JSON object",
            )

        input_type = payload.get("input_type")
        if not input_type:
            raise HTTPException(
                status_code=422,
                detail="Field 'input_type' is required",
            )

        if input_type in ("txt_file", "pdf_file"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input type '{input_type}' requires multipart/form-data file upload",
            )

        if input_type != "text_paste":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported input type '{input_type}'. Supported types: text_paste, txt_file, pdf_file",
            )

        content = payload.get("content")
        if content is None:
            raise HTTPException(
                status_code=422,
                detail="Field 'content' is required for input_type 'text_paste'",
            )
        raw_content = content

    elif "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:

        try:
            form = await request.form()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse multipart form data: {exc}",
            )

        input_type = form.get("input_type")
        if not input_type:
            raise HTTPException(
                status_code=422,
                detail="Form field 'input_type' is required",
            )


        if input_type == "text_paste":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input type 'text_paste' must be submitted as JSON, not file upload",
            )

        if input_type not in ("txt_file", "pdf_file"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported input type '{input_type}'. Supported types: text_paste, txt_file, pdf_file",
            )

        file_field = form.get("file")
        if not file_field or not hasattr(file_field, "read"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File upload in field 'file' is required for input type '{input_type}'",
            )

        filename = getattr(file_field, "filename", None)
        raw_content = await file_field.read()

    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported Content-Type. Expected application/json or multipart/form-data",
        )

    try:
        handler = InputHandlerFactory.get_handler(input_type)
        normalized_transcript = handler.extract_text(raw_content, filename=filename)
    except UnsupportedInputTypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (EmptyTranscriptError, TranscriptTooShortError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except InvalidFileFormatError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except TranscriptExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except FileSizeLimitExceededError as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except TranscriptInputError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


    job = Job(
        user_id=current_user.id,
        input_type=input_type,
        raw_transcript=normalized_transcript,
        status="pending",
        result=None,
        retry_count=0,
        completed_at=None,
    )

    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist job record",
        )

    try:
        process_job.delay(str(job.id))
    except Exception as exc:
        logger.error(f"Failed to enqueue task for job {job.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Job created in database, but failed to enqueue for asynchronous processing",
        )

    return job


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve status and result of a job",
)
async def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .filter(
            Job.id == job_id,
            Job.user_id == current_user.id,
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return job


