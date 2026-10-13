# Clinical Data Ingestion Pipeline

In-memory microservice for validating clinical DICOM files, inspecting medical imaging metadata, and extracting raw pixel matrices.

## Tech Stack
* **Runtime:** Python 3.14
* **API Framework:** FastAPI + Uvicorn (ASGI)
* **Data Validation:** Pydantic v2
* **Medical Imaging:** pydicom + NumPy
* **Quality Assurance:** Pytest, Mypy (strict mode), Ruff

## Development Setup

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install package in editable mode with dev dependencies
pip install --upgrade pip
pip install -e ".[dev]"

# 3. Run static analysis and linters
ruff check .
mypy src
