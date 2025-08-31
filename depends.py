from fastapi import Header, Request, HTTPException, status, Depends
from typing import Annotated

from config import VERIFY_USER_AGENT
from database.levels_db_access import LevelsDBAccessLayer
from database.users_db_access import UsersDBAccessLayer
from session.session_access import get_session_by_id
from session.models import Session

def is_valid_user(user_agent: Annotated[str | None, Header()] = None):
    """
    Verifica si el User-Agent de la solicitud es de un cliente válido.
    """
    if VERIFY_USER_AGENT:
        valid_agents = ("GameMaker", "Dalvik", "Android", "EngineBot", "PlayStation", "libcurl-agent")
        if not user_agent or not any(agent in user_agent for agent in valid_agents):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Illegal client."
            )
    elif user_agent is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Illegal client."
        )

def create_users_dal(request: Request) -> UsersDBAccessLayer:
    return UsersDBAccessLayer(request.app.state.users_db.async_session())

# The create_levels_dal dependency
# It now correctly accesses app.state.levels_db
def create_levels_dal(request: Request) -> LevelsDBAccessLayer:
    return LevelsDBAccessLayer(request.app.state.levels_db.async_session())

async def verify_and_get_session(request: Request) -> Session:
    """
    Verifica el código de autenticación y devuelve la sesión del usuario.
    """
    form_data = await request.form()
    auth_code = form_data.get("auth_code")
    
    if not auth_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Permission denied."
        )

    session = await get_session_by_id(auth_code)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired."
        )
    return session

def connection_count_inc(request: Request):
    """
    Incrementa el contador de conexiones activas.
    """
    request.app.state.connection_count += 1