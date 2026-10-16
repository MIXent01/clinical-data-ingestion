from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

PositiveDimension = Annotated[int, Field(ge=1)]


class DicomMetadata(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", str_strip_whitespace=True)

    patient_id: str = Field(min_length=1, default="UNKNOWN")
    modality: str = Field(min_length=2, max_length=16, default="UNKNOWN")
    # DICOM standard enforces a maximum length of 64 characters for UID values.
    study_instance_uid: str = Field(min_length=1, max_length=64)
    shape: tuple[PositiveDimension, ...] = Field(min_length=2)
    dtype: str = Field(min_length=1)
    min_pixel_value: float = Field(allow_inf_nan=False)
    max_pixel_value: float = Field(allow_inf_nan=False)
    is_c_contiguous: bool

    @model_validator(mode="after")
    def check_c_contiguous_and_max_pixel_less_than_min_pixel(self) -> DicomMetadata:
        if self.min_pixel_value > self.max_pixel_value:
            raise ValueError("max_pixel_value is less than min_pixel_value.")
        if not self.is_c_contiguous:
            raise ValueError("Pixels are not contiguous.")

        return self
