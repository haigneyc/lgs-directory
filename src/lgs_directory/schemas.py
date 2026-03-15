"""Pydantic schemas for data validation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AddressSchema(BaseModel):
    """Validates address data before writing to JSONB."""

    street: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    zip_code: str = Field(min_length=5, max_length=10, pattern=r"^\d{5}(-\d{4})?$")
