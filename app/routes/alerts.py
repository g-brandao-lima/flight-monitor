from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import RouteGroup
from app.services.alert_service import verify_silence_token

router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]


@router.get("/alerts/silence/{token}")
def silence_group(
    token: str,
    group_id: int = Query(...),
    db: DbDep = None,
):
    if not verify_silence_token(token, group_id):
        raise HTTPException(status_code=400, detail="Token invalido")

    group = db.get(RouteGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Grupo nao encontrado")

    group.silenced_until = datetime.utcnow() + timedelta(hours=24)
    db.commit()
    return {"message": f"Alertas do grupo '{group.name}' silenciados por 24 horas"}
