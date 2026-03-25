from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models import RouteGroup

MAX_ACTIVE_GROUPS = 10


def check_active_group_limit(db: Session, exclude_id: int | None = None) -> None:
    query = select(func.count()).select_from(RouteGroup).where(
        RouteGroup.is_active == True  # noqa: E712
    )
    if exclude_id is not None:
        query = query.where(RouteGroup.id != exclude_id)
    count = db.scalar(query)
    if count >= MAX_ACTIVE_GROUPS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum of {MAX_ACTIVE_GROUPS} active route groups reached.",
        )
