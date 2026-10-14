from fastapi import FastAPI

from app import api

app = FastAPI(title="Clinical Data Ingestion Pipeline", version="0.1.0")

app.include_router(api.router)
