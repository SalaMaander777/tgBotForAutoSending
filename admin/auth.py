import bcrypt
from fastapi import Cookie, Form, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from core.config import settings

COOKIE_NAME = "admin_session"
COOKIE_MAX_AGE = 60 * 60 * 8  # 8 hours


def _get_signer() -> TimestampSigner:
    return TimestampSigner(settings.secret_key)


def create_session_cookie(username: str) -> str:
    signer = _get_signer()
    return signer.sign(username).decode()


def verify_session_cookie(token: str) -> str | None:
    signer = _get_signer()
    try:
        value = signer.unsign(token, max_age=COOKIE_MAX_AGE)
        return value.decode()
    except (BadSignature, SignatureExpired):
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def require_auth(request: Request, admin_session: str | None = Cookie(default=None)) -> str:
    if admin_session is None:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/admin/login"},
        )
    username = verify_session_cookie(admin_session)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/admin/login"},
        )
    return username


async def login_handler(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
) -> Response:
    if username != settings.admin_username:
        return request.app.state.templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный логин или пароль"},
            status_code=401,
        )

    if not settings.admin_password_hash or not verify_password(password, settings.admin_password_hash):
        return request.app.state.templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный логин или пароль"},
            status_code=401,
        )

    token = create_session_cookie(username)
    response = RedirectResponse(url="/admin/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


async def logout_handler(request: Request) -> RedirectResponse:
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(COOKIE_NAME)
    return response
