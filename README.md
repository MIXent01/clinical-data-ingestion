# Clinical Data Ingestion Pipeline

![CI Status](https://github.com/MIXent01/clinical-data-ingestion/actions/workflows/ci.yml/badge.svg)

Production-ready, in-memory microservice for validating clinical DICOM files (PS3.10), inspecting medical imaging metadata, and extracting raw pixel statistics without disk I/O overhead.

## Key Engineering Decisions

- **Bounded Memory & OOM Protection:** Uploaded streams are capped by reading at most `MAX_FILE_SIZE_BYTES + 1` (`50 MB + 1 byte`), immediately rejecting oversized payloads with `413 Content Too Large` before full allocation.
- **Non-Blocking Event Loop:** CPU-bound DICOM parsing and NumPy array allocations (`parse_dicom_bytes`) are offloaded from the main `asyncio` event loop to a worker threadpool via `run_in_threadpool`.
- **C-Contiguous Memory Layout:** Pixel buffers are enforced into row-major C-contiguous memory (`np.ascontiguousarray`) to guarantee safe pointer arithmetic for downstream C/C++ imaging extensions.
- **Strict Domain Validation:** Output contracts use an immutable Pydantic v2 model (`DicomMetadata`) with `strict=True`, `frozen=True`, `extra="forbid"`, finite float enforcement (`allow_inf_nan=False`), and DICOM standard 64-character UID limits.
- **DICOM Type 2 Tag Resilience:** Missing or empty Type 2 tags (`PatientID`, `Modality`) safely fall back to `"UNKNOWN"`, preventing `str(None)` serialization bugs.
- **Container Hardening:** Packaged in `python:3.14-slim` running under an unprivileged `appuser` account with exec-form `CMD` for clean `SIGTERM` handling.

## Tech Stack

- **Runtime:** Python 3.14
- **API Framework:** FastAPI + Uvicorn (ASGI)
- **Data Validation:** Pydantic v2
- **Medical Imaging:** pydicom + NumPy
- **Quality Assurance:** Pytest (`httpx2`), Mypy (strict mode), Ruff, GitHub Actions CI
- **Containerization:** Docker

## API Reference

### 1. Health Check
```http
GET /health
```
Verifies that the microservice is alive and ready to accept requests.

**Response (`200 OK`):**
```json
{
  "status": "ok"
}
```

### 2. Inspect DICOM File
```http
POST /api/v1/dicom/inspect
```
Accepts a `multipart/form-data` DICOM file upload (`file`), validates format and domain constraints in memory, and returns extracted metadata and pixel statistics.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/dicom/inspect" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.dcm;type=application/dicom"
```

**Success Response (`200 OK`):**
```json
{
  "patient_id": "PATIENT_001",
  "modality": "CT",
  "study_instance_uid": "1.2.840.113619.2.1",
  "shape": [512, 512],
  "dtype": "uint16",
  "min_pixel_value": 0.0,
  "max_pixel_value": 2048.0,
  "is_c_contiguous": true
}
```

**Error Responses:**
- `400 Bad Request` – Empty byte stream, corrupted DICOM header, missing/empty pixel array, or failed domain validation (`DicomIngestionError`).
- `413 Content Too Large` – Uploaded file exceeds the 50 MB size limit.
- `422 Unprocessable Content` – Missing `file` field in `multipart/form-data` request.

## Local Development Setup

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install package in editable mode with dev dependencies
pip install --upgrade pip
pip install -e ".[dev]"

# 3. Run code formatting, linters, and strict type checking
ruff format --check .
ruff check .
mypy --strict src tests

# 4. Run integration test suite
pytest -v

# 5. Start development server locally
uvicorn app.main:app --reload
```

## Running with Docker

```bash
# 1. Build production container image
docker build -t clinical-dicom-pipeline:0.1.0 .

# 2. Run container on port 8000
docker run --rm -p 8000:8000 clinical-dicom-pipeline:0.1.0
```
Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.
