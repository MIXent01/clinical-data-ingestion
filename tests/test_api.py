from io import BytesIO

import numpy as np
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydicom import dcmwrite
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import UID, ExplicitVRLittleEndian

from app.main import app

client = TestClient(app)


def _create_synthetic_dicom_bytes(
    study_uid: str = "1.2.840.113619.2.1", include_pixels: bool = True
) -> bytes:
    buffer = BytesIO()

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = UID("1.2.840.10008.5.1.4.1.1.2")
    file_meta.MediaStorageSOPInstanceUID = UID("1.2.3.4.5.6.7")
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    file_dataset = FileDataset(buffer, {}, preamble=b"\x00" * 128, file_meta=file_meta)
    file_dataset.PatientID = "PATIENT_001"
    file_dataset.Modality = "CT"
    file_dataset.StudyInstanceUID = study_uid

    pixels = np.array([[10, 20], [30, 40]], dtype=np.uint16)
    file_dataset.Rows = 2
    file_dataset.Columns = 2
    file_dataset.PhotometricInterpretation = "MONOCHROME2"
    file_dataset.BitsAllocated = 16
    file_dataset.BitsStored = 16
    file_dataset.HighBit = 15
    file_dataset.PixelRepresentation = 0
    file_dataset.SamplesPerPixel = 1
    if include_pixels:
        file_dataset.PixelData = pixels.tobytes()

    dcmwrite(buffer, file_dataset, enforce_file_format=True)

    return buffer.getvalue()


def test_read_health() -> None:
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_post_dicom_exceeds_size_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.MAX_FILE_SIZE_BYTES", 100)
    response = client.post(
        "/api/v1/dicom/inspect", files={"file": ("large.dcm", b"a" * 101, "application/dicom")}
    )
    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE


def test_post_dicom_invalid_byte_stream() -> None:
    response = client.post(
        "/api/v1/dicom/inspect",
        files={"file": ("corrupted.dcm", b"not a dicom file", "application/dicom")},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Failed to parse DICOM byte stream."


def test_post_dicom_valid_file() -> None:
    dicom_valid_file = _create_synthetic_dicom_bytes()

    response = client.post(
        "/api/v1/dicom/inspect",
        files={"file": ("valid.dcm", dicom_valid_file, "application/dicom")},
    )

    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["patient_id"] == "PATIENT_001"
    assert data["modality"] == "CT"
    assert data["shape"] == [2, 2]
    assert data["min_pixel_value"] == 10
    assert data["max_pixel_value"] == 40
    assert data["is_c_contiguous"] is True
    assert data["study_instance_uid"] == "1.2.840.113619.2.1"
    assert data["dtype"] == "uint16"


def test_post_dicom_missing_study_uid() -> None:
    dicom_missing_study_uid = _create_synthetic_dicom_bytes(study_uid="")

    response = client.post(
        "/api/v1/dicom/inspect",
        files={"file": ("invalid.dcm", dicom_missing_study_uid, "application/dicom")},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "DICOM metadata failed domain validation."


def test_post_dicom_empty_file() -> None:
    response = client.post(
        "/api/v1/dicom/inspect", files={"file": ("invalid.dcm", b"", "application/dicom")}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Empty DICOM byte stream provided."


def test_post_dicom_missing_pixel_data() -> None:
    dicom_missing_pixel_data = _create_synthetic_dicom_bytes(include_pixels=False)

    response = client.post(
        "/api/v1/dicom/inspect",
        files={"file": ("missing_pixel.dcm", dicom_missing_pixel_data, "application/dicom")},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "No valid pixel data in DICOM file."
