import datetime
from sqlalchemy import JSON, String, Integer, Float, Boolean, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column
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
