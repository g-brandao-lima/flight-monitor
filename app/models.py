import datetime
from sqlalchemy import JSON, String, Integer, Float, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class RouteGroup(Base):
    __tablename__ = "route_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    origins: Mapped[list] = mapped_column(JSON)
    destinations: Mapped[list] = mapped_column(JSON)
    duration_days: Mapped[int] = mapped_column(Integer)
    travel_start: Mapped[datetime.date] = mapped_column(Date)
    travel_end: Mapped[datetime.date] = mapped_column(Date)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FlightSnapshot(Base):
    __tablename__ = "flight_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    route_group_id: Mapped[int] = mapped_column(ForeignKey("route_groups.id"))
    origin: Mapped[str] = mapped_column(String(3))
    destination: Mapped[str] = mapped_column(String(3))
    departure_date: Mapped[datetime.date] = mapped_column(Date)
    return_date: Mapped[datetime.date] = mapped_column(Date)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    airline: Mapped[str] = mapped_column(String(2))
    price_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_first_quartile: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_third_quartile: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_classification: Mapped[str | None] = mapped_column(String(10), nullable=True)
    collected_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    route_group: Mapped["RouteGroup"] = relationship("RouteGroup", backref="snapshots")
    booking_classes: Mapped[list["BookingClassSnapshot"]] = relationship(
        "BookingClassSnapshot", backref="flight_snapshot", cascade="all, delete-orphan"
    )


class BookingClassSnapshot(Base):
    __tablename__ = "booking_class_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    flight_snapshot_id: Mapped[int] = mapped_column(ForeignKey("flight_snapshots.id"))
    class_code: Mapped[str] = mapped_column(String(1))
    seats_available: Mapped[int] = mapped_column(Integer)
    segment_direction: Mapped[str] = mapped_column(String(10))
