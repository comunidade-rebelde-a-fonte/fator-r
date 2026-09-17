import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field

from fator_r.api.deps import CurrentUser, DbSession
from fator_r.core.rate_limit import LoginRateLimiter
from fator_r.core.security import hash_token, new_session_token, verify_password
from fator_r.core.settings import Settings, get_settings
from fator_r.repositories.auth import create_session, delete_session, get_user_by_email

public_router = APIRouter(prefix="/auth", tags=["auth"])
router = APIRouter(prefix="/auth", tags=["auth"])

_settings = get_settings()
login_rate_limiter = LoginRateLimiter(
    _settings.login_rate_limit_attempts, _settings.login_rate_limit_window_seconds
)

CREDENCIAIS_INVALIDAS = "Credenciais inválidas"


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=1024)


class MeOut(BaseModel):
    id: uuid.UUID
    firm_id: uuid.UUID
    email: str
    nome: str


@public_router.post("/login", response_model=MeOut)
async def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> MeOut:
    ip = request.client.host if request.client else "desconhecido"
    if login_rate_limiter.is_blocked(ip, payload.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Tente novamente mais tarde.",
        )

    user = await get_user_by_email(session, payload.email)
    password_ok = verify_password(user.senha_hash if user else None, payload.senha)
    if user is None or not password_ok or not user.ativo:
        login_rate_limiter.register_failure(ip, payload.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=CREDENCIAIS_INVALIDAS)

    login_rate_limiter.reset(ip, payload.email)
    token = new_session_token()
    ttl = timedelta(hours=settings.session_ttl_hours)
    await create_session(session, user.id, hash_token(token), ttl)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=int(ttl.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return MeOut(id=user.id, firm_id=user.firm_id, email=user.email, nome=user.nome)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: CurrentUser,
    request: Request,
    response: Response,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await delete_session(session, hash_token(token))
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser) -> MeOut:
    return MeOut(id=user.id, firm_id=user.firm_id, email=user.email, nome=user.nome)
