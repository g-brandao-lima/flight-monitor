from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def get_required_user(
    current_user: User | None = Depends(get_current_user),
) -> User:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return current_user


def get_admin_user(
    current_user: User = Depends(get_required_user),
) -> User:
    """Permite acesso apenas ao email configurado em ADMIN_EMAIL.

    Retorna 404 (nao 403) para nao-admins, evitando enumeracao de rotas admin.
    """
    from app.config import settings
    admin_email = (settings.admin_email or "").strip().lower()
    user_email = (current_user.email or "").strip().lower()
    if not admin_email or user_email != admin_email:
        raise HTTPException(status_code=404, detail="Not found")
    return current_user


def is_admin(user: User | None) -> bool:
    """Helper para templates: usuario e admin?"""
    if user is None:
        return False
    from app.config import settings
    admin_email = (settings.admin_email or "").strip().lower()
    user_email = (user.email or "").strip().lower()
    return bool(admin_email) and user_email == admin_email
