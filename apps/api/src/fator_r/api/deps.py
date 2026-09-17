from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.core.db import firm_session, get_session
from fator_r.core.security import hash_token
from fator_r.core.settings import get_settings
from fator_r.repositories.auth import AuthenticatedUser, get_user_by_session_token

DbSession = Annotated[AsyncSession, Depends(get_session)]


async def require_user(request: Request, session: DbSession) -> AuthenticatedUser:
    """Resolve a sessão do cookie. Sem sessão válida: 401."""
    token = request.cookies.get(get_settings().session_cookie_name)
    if token:
        user = await get_user_by_session_token(session, hash_token(token))
        if user is not None:
            request.state.user = user
            request.state.firm_id = user.firm_id
            return user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")


CurrentUser = Annotated[AuthenticatedUser, Depends(require_user)]


async def get_firm_session(user: CurrentUser) -> AsyncIterator[AsyncSession]:
    """Sessão do banco amarrada ao escritório do usuário (app.firm_id em toda transação)."""
    async with firm_session(user.firm_id) as session:
        yield session


FirmSession = Annotated[AsyncSession, Depends(get_firm_session)]
