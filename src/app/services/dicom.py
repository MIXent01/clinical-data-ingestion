from io import BytesIO

import numpy as np
import pydicom
from pydantic import ValidationError
from pydicom.errors import InvalidDicomError

from app.schemas import DicomMetadata


class DicomIngestionError(Exception):
    """Base exception for errors during DICOM bytes stream parsing."""


def parse_dicom_bytes(raw_bytes: bytes) -> DicomMetadata:
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
        # Enforce C-contiguous (row-major) memory layout for
        # safe pointer arithmetic in downstream C/C++ extensions.
        contiguous_pixels = np.ascontiguousarray(raw_pixels)
    except (AttributeError, ValueError, RuntimeError) as err:
        raise DicomIngestionError("No valid pixel data in DICOM file.") from err

    if contiguous_pixels.size == 0:
        raise DicomIngestionError("Pixel array in DICOM is empty.")

    try:
        return DicomMetadata(
            # Handle DICOM Type 2 tags that may exist with a None or empty value,
            # preventing str(None) from producing "None".
            patient_id=str(dataset.get("PatientID") or "UNKNOWN"),
            modality=str(dataset.get("Modality") or "UNKNOWN"),
            study_instance_uid=str(dataset.get("StudyInstanceUID") or ""),
            shape=tuple(contiguous_pixels.shape),
            dtype=str(contiguous_pixels.dtype),
            min_pixel_value=float(contiguous_pixels.min()),
            max_pixel_value=float(contiguous_pixels.max()),
            is_c_contiguous=bool(contiguous_pixels.flags["C_CONTIGUOUS"]),
        )
    except ValidationError as err:
        raise DicomIngestionError("DICOM metadata failed domain validation.") from err
