from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RouteGroup
from app.schemas import RouteGroupCreate, RouteGroupUpdate, RouteGroupResponse
from app.services.route_group_service import check_active_group_limit

router = APIRouter(prefix="/route-groups", tags=["route-groups"])
DbDep = Annotated[Session, Depends(get_db)]


@router.post("/", response_model=RouteGroupResponse, status_code=201)
def create_route_group(data: RouteGroupCreate, db: DbDep):
    check_active_group_limit(db)
    group = RouteGroup(**data.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/", response_model=list[RouteGroupResponse])
def list_route_groups(db: DbDep):
    return db.query(RouteGroup).all()


@router.get("/{group_id}", response_model=RouteGroupResponse)
def get_route_group(group_id: int, db: DbDep):
    group = db.get(RouteGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Route group not found")
    return group


@router.patch("/{group_id}", response_model=RouteGroupResponse)
def update_route_group(group_id: int, data: RouteGroupUpdate, db: DbDep):
    group = db.get(RouteGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Route group not found")
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("is_active") is True and not group.is_active:
        check_active_group_limit(db, exclude_id=group.id)
    for key, value in update_data.items():
        setattr(group, key, value)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=204)
def delete_route_group(group_id: int, db: DbDep):
    group = db.get(RouteGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Route group not found")
    db.delete(group)
    db.commit()
