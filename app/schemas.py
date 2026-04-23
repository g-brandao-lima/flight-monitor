import datetime
import re
from datetime import date, timedelta
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

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


class LegCreate(BaseModel):
    order: int
    origin: str
    destination: str
    window_start: date
    window_end: date
    min_stay_days: int
    max_stay_days: int | None = None
    max_stops: int | None = None


class LegOut(LegCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class RouteGroupMultiCreate(BaseModel):
    name: str
    passengers: int = 1
    target_price: float | None = None
    legs: list[LegCreate]

    @model_validator(mode="after")
    def validate_chain(self) -> "RouteGroupMultiCreate":
        if not (2 <= len(self.legs) <= 5):
            raise ValueError("Roteiro multi-trecho exige entre 2 e 5 trechos.")
        sorted_legs = sorted(self.legs, key=lambda l: l.order)
        for leg in sorted_legs:
            if leg.min_stay_days < 1:
                raise ValueError("Estadia minima precisa ser de pelo menos 1 dia.")
            if leg.max_stay_days is not None and leg.max_stay_days < leg.min_stay_days:
                raise ValueError("Estadia maxima nao pode ser menor que a minima.")
            if len(leg.origin) != 3 or len(leg.destination) != 3:
                raise ValueError(
                    "Codigo IATA deve ter 3 letras (exemplo: GRU, FCO, MAD)."
                )
        for i in range(1, len(sorted_legs)):
            prev = sorted_legs[i - 1]
            cur = sorted_legs[i]
            min_start = prev.window_end + timedelta(days=prev.min_stay_days)
            if cur.window_start < min_start:
                raise ValueError(
                    f"Trecho {cur.order} precisa sair em ou apos "
                    f"{min_start.strftime('%d/%m/%Y')}. "
                    f"Ajuste a janela ou reduza a estadia minima do trecho {prev.order}."
                )
        return self
