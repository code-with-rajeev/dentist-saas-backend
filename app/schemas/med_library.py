# Standard library
import uuid

# Third-party
from pydantic import BaseModel, Field, field_validator


class MedLibraryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    dosage: str | None = Field(None, max_length=100)
    frequency: str | None = Field(None, max_length=100)
    duration: str | None = Field(None, max_length=100)
    instructions: str | None = Field(None, max_length=500)

# dentist_id excluded from response intentionally - frontend never needs it.
class MedLibraryResponse(BaseModel):
    id: uuid.UUID
    name: str
    dosage: str | None
    frequency: str | None
    duration: str | None
    instructions: str | None
    category: str | None  # NULL for custom meds, set for system meds
    source: str        # 'system' | 'custom' - frontend uses this for 🟢/🔵 dot
    usage_count: int

    model_config = {"from_attributes": True}

class MedLibraryUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    dosage: str | None = Field(None, max_length=100)
    frequency: str | None = Field(None, max_length=100)
    duration: str | None = Field(None, max_length=100)
    instructions: str | None = Field(None, max_length=500)

    @field_validator("name")
    def name_cannot_be_empty(cls, v):
        if v is not None and v.strip() == "":
            raise ValueError("Name cannot be empty")
        return v