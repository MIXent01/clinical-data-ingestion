from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from app.schemas import DicomMetadata
from app.services.dicom import DicomIngestionError, parse_dicom_bytes

MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024

router = APIRouter()


@router.get("/health")
async def read_health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/v1/dicom/inspect")
async def post_dicom(file: UploadFile) -> DicomMetadata:
    # Read at most MAX_FILE_SIZE_BYTES + 1 bytes to detect oversized payloads and prevent OOM.
    raw_bytes = await file.read(MAX_FILE_SIZE_BYTES + 1)

    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="DICOM file exceeds the 50 MB size limit.",
        )

    try:
        # Offload CPU-bound DICOM parsing to a worker threadpool,
        # so we can avoid blocking the main asyncio event loop.
        return await run_in_threadpool(parse_dicom_bytes, raw_bytes)
    except DicomIngestionError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
