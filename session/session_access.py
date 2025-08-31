from session.models import Session, deserialize_session
from common import ClientType
from time import time
from typing import Dict, Optional

from locales import get_locale_model

# Diccionarios para simular el almacenamiento en memoria en lugar de Redis
# session_data: Mapea session_id a objetos de sesión
# user_session_ids: Mapea user_id a session_id
session_data: Dict[str, Session] = {}
user_session_ids: Dict[int, str] = {}


def generate_session_id(user_id: int) -> str:
    """Generates a unique session ID based on user ID and current time."""
    return hex(int(f"{user_id}{str(int(time()))[2:]}")).upper()[2:]

async def new_session(
        username: str,
        user_id: int,
        mobile: bool,
        client_type: ClientType,
        locale: str,
        proxied: bool
) -> Session:
    """Creates a new session for a user and stores it in memory."""
    session = Session(
        session_id=generate_session_id(user_id),
        username=username,
        user_id=user_id,
        mobile=mobile,
        client_type=client_type.value,
        locale=locale,
        proxied=proxied
    )
    
    # Drop previous session if it exists
    await drop_session_by_id(user_session_ids.get(user_id))
    
    # Store the new session and its mapping in memory
    session_data[session.session_id] = session
    user_session_ids[user_id] = session.session_id
    
    return session

async def get_session_by_id(
        session_id: str
) -> Optional[Session]:
    """Retrieves a session from memory by its session ID."""
    return session_data.get(session_id)

async def drop_session_by_id(
        session_id: str
) -> bool:
    """Deletes a session from memory by its session ID and removes the user-to-session mapping."""
    if session_id in session_data:
        session = session_data.pop(session_id)
        if session.user_id in user_session_ids:
            del user_session_ids[session.user_id]
        return True
    return False

async def get_session_id_by_user_id(
        user_id: int
) -> Optional[str]:
    """Retrieves a session ID from memory by its user ID."""
    return user_session_ids.get(user_id)