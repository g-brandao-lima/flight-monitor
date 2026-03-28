from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.oauth import oauth
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        return RedirectResponse(url="/?msg=login_erro", status_code=303)

    userinfo = token.get("userinfo")
    if not userinfo:
        return RedirectResponse(url="/?msg=login_erro", status_code=303)

    user = db.query(User).filter(User.google_id == userinfo["sub"]).first()
    if not user:
        user = User(
            google_id=userinfo["sub"],
            email=userinfo["email"],
            name=userinfo.get("name", ""),
            picture_url=userinfo.get("picture"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
