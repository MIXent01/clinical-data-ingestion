from io import BytesIO
from typing import Any

import numpy as np
import pydicom
from pydicom.errors import InvalidDicomError


class DicomIngestionError(Exception):
    """Base exception for errors during DICOM bytes stream parsing."""


def parse_dicom_bytes(raw_bytes: bytes) -> dict[str, Any]:
    """Parse raw DICOM bytes in memory and extract metadata and pixel statistics."""

    if not raw_bytes:
        raise DicomIngestionError("Empty DICOM byte stream provided.")

    try:
        buffer = BytesIO(raw_bytes)
        dataset = pydicom.dcmread(buffer, force=False)
    except (InvalidDicomError, EOFError, ValueError, OSError) as err:
        raise DicomIngestionError("Failed to parse DICOM byte stream.") from err

    try:
        raw_pixels = dataset.pixel_array
        contiguous_pixels = np.ascontiguousarray(raw_pixels)
    except (AttributeError, ValueError, RuntimeError) as err:
        raise DicomIngestionError("No valid pixel data in DICOM file.") from err

    if contiguous_pixels.size == 0:
        raise DicomIngestionError("Pixel array in DICOM is empty.")

    return {
        "patient_id": str(dataset.get("PatientID") or "UNKNOWN"),
        "modality": str(dataset.get("Modality") or "UNKNOWN"),
        "study_instance_uid": str(dataset.get("StudyInstanceUID") or ""),
        "shape": list(contiguous_pixels.shape),
        "dtype": str(contiguous_pixels.dtype),
        "min_pixel_value": float(contiguous_pixels.min()),
        "max_pixel_value": float(contiguous_pixels.max()),
        "is_c_contiguous": bool(contiguous_pixels.flags["C_CONTIGUOUS"]),
    }
