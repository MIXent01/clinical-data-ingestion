from fastapi import FastAPI

from app import api

app = FastAPI(
    title="Clinical Data Ingestion Pipeline",
    version="0.1.0",
    description="Microservice for in-memory DICOM file inspection, domain validation "
    "and pixel statistics extraction.",
)

app.include_router(api.router)
