from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.dependencies import get_required_user
from app.database import get_db
from app.models import RouteGroup, User
from app.schemas import RouteGroupCreate, RouteGroupUpdate, RouteGroupResponse
from app.services.route_group_service import check_active_group_limit

router = APIRouter(prefix="/route-groups", tags=["route-groups"])
DbDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[User, Depends(get_required_user)]


def get_user_group_or_404(group_id: int, user: User, db: Session) -> RouteGroup:
    """Fetch a RouteGroup by ID owned by the user, or raise 404.

    Returns 404 (not 403) even when the group exists for another user,
    to avoid leaking existence of resources across users.
    """
    group = (
        db.query(RouteGroup)
        .filter(RouteGroup.id == group_id, RouteGroup.user_id == user.id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Route group not found")
    return group


@router.post("/", response_model=RouteGroupResponse, status_code=201)
def create_route_group(data: RouteGroupCreate, user: UserDep, db: DbDep):
    check_active_group_limit(db, user_id=user.id)
    group = RouteGroup(**data.model_dump(), user_id=user.id)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/", response_model=list[RouteGroupResponse])
def list_route_groups(user: UserDep, db: DbDep):
    return db.query(RouteGroup).filter(RouteGroup.user_id == user.id).all()


@router.get("/{group_id}", response_model=RouteGroupResponse)
def get_route_group(group_id: int, user: UserDep, db: DbDep):
    return get_user_group_or_404(group_id, user, db)


@router.patch("/{group_id}", response_model=RouteGroupResponse)
def update_route_group(
    group_id: int, data: RouteGroupUpdate, user: UserDep, db: DbDep
):
    group = get_user_group_or_404(group_id, user, db)
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("is_active") is True and not group.is_active:
        check_active_group_limit(db, user_id=user.id, exclude_id=group.id)
    for key, value in update_data.items():
        setattr(group, key, value)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=204)
def delete_route_group(group_id: int, user: UserDep, db: DbDep):
    group = get_user_group_or_404(group_id, user, db)
    db.delete(group)
    db.commit()
