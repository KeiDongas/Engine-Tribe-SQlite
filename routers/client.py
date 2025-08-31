from fastapi import Form, Depends, HTTPException, status
from typing import Annotated

from routers.api_router import APIRouter

from config import API_KEY
from models import (
    ClientSuccessMessage,
    ClientListMessage
)
from locales import get_locale_model
from common import (
    ClientType
)
from database.users_db_access import UsersDBAccessLayer
from database.models import Client
from depends import create_users_dal, connection_count_inc

router = APIRouter(
    prefix="/client",
    dependencies=[Depends(connection_count_inc)]
)

@router.post("/new")
async def client_new_handler(
    api_key: Annotated[str, Form()],
    token: Annotated[str, Form()],
    client_type: Annotated[str, Form()],
    locale: Annotated[str, Form()],
    mobile: Annotated[bool, Form()],
    proxied: Annotated[bool, Form()],
    dal: Annotated[UsersDBAccessLayer, Depends(create_users_dal)]
):
    """Crea un nuevo cliente para la API."""
    if api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key.")
    
    client_type_upper = client_type.upper()
    if client_type_upper not in ClientType.__members__:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client type.")
    
    locale_model = get_locale_model(locale)
    if not locale_model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid locale.")
    
    client_type_value = ClientType[client_type_upper].value
    
    await dal.new_client(
        token=token,
        client_type=client_type_value,
        locale=locale,
        mobile=mobile,
        proxied=proxied
    )
    await dal.commit()
    
    return ClientSuccessMessage(
        success="Successfully created client.",
        token=token,
        client_type=client_type_upper,
        locale=locale,
        mobile=mobile,
        proxied=proxied
    )

@router.post("/list")
async def client_list_handler(
    api_key: Annotated[str, Form()],
    dal: Annotated[UsersDBAccessLayer, Depends(create_users_dal)]
):
    """Lista todos los clientes de la API."""
    if api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key.")
    
    clients: list[Client] = await dal.get_all_clients()
    
    return ClientListMessage(
        result=[
            ClientSuccessMessage(
                success=None,
                token=client.token,
                client_type=ClientType(client.type).name,
                locale=client.locale,
                mobile=client.mobile,
                proxied=client.proxied
            ) for client in clients
        ]
    )

@router.post("/{token}/revoke")
async def client_revoke_handler(
    token: str,
    api_key: Annotated[str, Form()],
    dal: Annotated[UsersDBAccessLayer, Depends(create_users_dal)]
):
    """Revoca un token de cliente."""
    if api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key.")
    
    client: Client | None = await dal.get_client_by_token(token=token)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    
    await dal.revoke_client(client=client)
    await dal.commit()
    
    return ClientSuccessMessage(
        success="Successfully revoked client.",
        token=token
    )

@router.post("/{token}/delete")
async def client_delete_handler(
    token: str,
    api_key: Annotated[str, Form()],
    dal: Annotated[UsersDBAccessLayer, Depends(create_users_dal)]
):
    """Elimina un cliente de la base de datos."""
    if api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key.")
    
    client: Client | None = await dal.get_client_by_token(token=token)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    
    await dal.delete_client(client=client)
    await dal.commit()
    
    return ClientSuccessMessage(
        success="Successfully deleted client.",
        token=token
    )