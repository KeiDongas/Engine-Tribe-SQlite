from fastapi import Form, Depends, Request, HTTPException, status
from typing import Annotated

from routers.api_router import APIRouter

from config import API_KEY, ENABLE_DISCORD_WEBHOOK, ENABLE_ENGINE_BOT_WEBHOOK, DISCORD_SERVER_NAME
from models import (
    UserLoginProfile,
    LegacyUserLoginProfile,
    UserPermissionSuccessMessage,
    UserSuccessMessage,
    UserInfoMessage,
    UserInfo
)
from locales import get_locale_model
from common import (
    ClientType,
    calculate_password_hash,
)
from push import (
    push_to_engine_bot,
    push_to_engine_bot_discord
)
from database.users_db_access import UsersDBAccessLayer
from database.models import User, Client
from session.session_access import new_session
from depends import (
    create_users_dal,
    connection_count_inc
)

router = APIRouter(
    prefix="/user",
    dependencies=[Depends(connection_count_inc)]
)

async def get_user_from_identifier(
    dal: UsersDBAccessLayer,
    user_identifier: str
) -> User | None:
    """Busca un usuario por su ID de IM o nombre de usuario."""
    if user_identifier.isnumeric():
        return await dal.get_user_by_im_id(im_id=int(user_identifier))
    else:
        return await dal.get_user_by_username(username=user_identifier)

@router.post("/login")
async def user_login_handler(
    request: Request,
    alias: Annotated[str, Form()],
    token: Annotated[str, Form()],
    password: Annotated[str, Form()],
    dal: Annotated[UsersDBAccessLayer, Depends(create_users_dal)]
):
    """Maneja el inicio de sesión del usuario."""
    client: Client | None = await dal.get_client_by_token(token=token)
    if not client or not client.valid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Illegal client.")
    
    locale_model = get_locale_model(client.locale)
    client_type = ClientType(client.type)
    
    user: User
    if client_type == ClientType.ENGINE_BOT:
        user = User(
            id=0,
            username="EngineBot",
            im_id=0,
            password_hash="",
            uploads=0,
            is_valid=True,
            is_banned=False,
            is_admin=False,
            is_mod=True,
            is_booster=False,
        )
    else:
        user = await dal.get_user_by_username(username=alias)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=locale_model.ACCOUNT_NOT_FOUND)
        
        if not user.is_valid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=locale_model.ACCOUNT_IS_NOT_VALID)
        if user.is_banned:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=locale_model.ACCOUNT_BANNED)
        if user.password_hash != calculate_password_hash(password.encode("latin1").decode("utf-8")):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=locale_model.ACCOUNT_ERROR_PASSWORD)

    session = await new_session(
        username=user.username,
        user_id=user.id,
        mobile=client.mobile,
        client_type=client_type,
        locale=client.locale,
        proxied=client.proxied
    )
    auth_code: str = session.session_id

    if client_type is ClientType.LEGACY:
        return LegacyUserLoginProfile(
            alias=alias,
            id=user.im_id,
            auth_code=auth_code,
            goomba=True,
            ip=request.client.host
        )
    else:
        return UserLoginProfile(
            username=alias,
            admin=user.is_admin,
            mod=user.is_mod,
            booster=user.is_booster,
            goomba=True,
            alias=alias,
            id=str(user.im_id),
            uploads=user.uploads,
            mobile=client.mobile,
            auth_code=auth_code,
        )

@router.post("/register")
async def user_register_handler(
    api_key: Annotated[str, Form()],
    im_id: Annotated[int, Form()],
    username: Annotated[str, Form()],
    password_hash: Annotated[str, Form()],
    dal: Annotated[UsersDBAccessLayer, Depends(create_users_dal)]
):
    """Registra una nueva cuenta de usuario."""
    if api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key.")
    
    if await dal.get_user_by_im_id(im_id=im_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User ID already exists.")
    
    if await dal.get_user_by_username(username=username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")

    await dal.add_user(
        username=username,
        password_hash=password_hash,
        im_id=im_id
    )
    await dal.commit()
    
    return UserSuccessMessage(
        success="Registration success.",
        username=username,
        im_id=str(im_id),
        type="register"
    )

@router.post("/{user_identifier}/permission/{permission}")
async def user_set_permission_handler(
    user_identifier: str,
    permission: str,
    api_key: Annotated[str, Form()],
    value: Annotated[bool, Form()],
    dal: Annotated[UsersDBAccessLayer, Depends(create_users_dal)]
):
    """Actualiza los permisos de un usuario."""
    if api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key.")

    user: User | None = await get_user_from_identifier(user_identifier=user_identifier, dal=dal)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    key_permission_changed: bool = False
    
    match permission:
        case "mod":
            if user.is_mod != value: key_permission_changed = True
            user.is_mod = value
        case "admin":
            user.is_admin = value
        case "booster":
            if user.is_booster != value: key_permission_changed = True
            user.is_booster = value
        case "valid":
            user.is_valid = value
        case "banned":
            user.is_banned = value
        case _:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Permission does not exist.")

    await dal.update_user(user=user)
    await dal.commit()

    if key_permission_changed:
        if ENABLE_ENGINE_BOT_WEBHOOK:
            await push_to_engine_bot({
                'type': 'permission_change',
                'permission': permission,
                'username': user.username,
                'value': value
            })
        if ENABLE_DISCORD_WEBHOOK:
            emoji = '🤗' if value else '😥'
            role_name = "Booster" if permission == 'booster' else "Stage Moderator"
            await push_to_engine_bot_discord(
                f"{emoji} **{user.username}** ahora {'sí' if value else 'no'} "
                f"tiene el rol **{role_name}** en {DISCORD_SERVER_NAME}!!"
            )
            
    return UserPermissionSuccessMessage(
        success="Permission updated.",
        type="update",
        username=user.username,
        im_id=str(user.im_id),
        permission=permission,
        value=value
    )

@router.post("/{user_identifier}/update_password")
async def user_update_password_handler(
    user_identifier: str,
    im_id: Annotated[int, Form()],
    password_hash: Annotated[str, Form()],
    api_key: Annotated[str, Form()],
    dal: Annotated[UsersDBAccessLayer, Depends(create_users_dal)]
):
    """Actualiza la contraseña de un usuario."""
    if api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key.")

    user: User | None = await get_user_from_identifier(user_identifier=user_identifier, dal=dal)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    if user.im_id != im_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User incorrect.")

    user.password_hash = password_hash
    await dal.update_user(user=user)
    await dal.commit()
    
    return UserSuccessMessage(
        success="Update password success.",
        type="update",
        username=user.username,
        im_id=str(user.im_id)
    )

@router.post("/{user_identifier}/info")
async def user_info_handler(
    user_identifier: str,
    dal: Annotated[UsersDBAccessLayer, Depends(create_users_dal)]
):
    """Obtiene la información de un usuario."""
    user: User | None = await get_user_from_identifier(user_identifier=user_identifier, dal=dal)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        
    return UserInfoMessage(
        result=UserInfo(
            username=user.username,
            im_id=user.im_id,
            uploads=user.uploads,
            is_admin=user.is_admin,
            is_mod=user.is_mod,
            is_booster=user.is_booster,
            is_valid=user.is_valid,
            is_banned=user.is_banned
        )
    )