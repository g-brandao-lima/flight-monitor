import datetime
import re
from pydantic import BaseModel, field_validator

IATA_PATTERN = re.compile(r"^[A-Z]{3}$")


class RouteGroupCreate(BaseModel):
    name: str
    origins: list[str]
    destinations: list[str]
    duration_days: int
    travel_start: datetime.date
    travel_end: datetime.date
    target_price: float | None = None

    @field_validator("origins", "destinations")
    @classmethod
    def validate_iata_codes(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one IATA code is required")
        for code in v:
            if not IATA_PATTERN.match(code):
                raise ValueError(
                    f"Invalid IATA code: {code}. Must be 3 uppercase letters."
                )
        return v

    @field_validator("duration_days")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Duration must be at least 1 day")
        return v


class RouteGroupUpdate(BaseModel):
    name: str | None = None
    origins: list[str] | None = None
    destinations: list[str] | None = None
    duration_days: int | None = None
    travel_start: datetime.date | None = None
    travel_end: datetime.date | None = None
    target_price: float | None = None
    is_active: bool | None = None

    @field_validator("origins", "destinations")
    @classmethod
    def validate_iata_codes(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if not v:
            raise ValueError("At least one IATA code is required")
        for code in v:
            if not IATA_PATTERN.match(code):
                raise ValueError(f"Invalid IATA code: {code}")
        return v


class RouteGroupResponse(BaseModel):
    id: int
    name: str
    origins: list[str]
    destinations: list[str]
    duration_days: int
    travel_start: datetime.date
    travel_end: datetime.date
    target_price: float | None
    is_active: bool

    model_config = {"from_attributes": True}
