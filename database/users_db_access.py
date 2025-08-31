from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Client
from sqlalchemy import func, select, delete
from sqlalchemy import or_


class UsersDBAccessLayer:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_user(self, user: User):
        self.session.add(user)
        await self.session.flush()

    async def add_user(self, username: str, password_hash: str, im_id: int):
        # register user
        user = User(username=username, password_hash=password_hash, im_id=im_id, uploads=0, is_admin=False,
                    is_mod=False, is_booster=False, is_valid=True, is_banned=False)

        self.session.add(user)
        await self.session.flush()

    async def get_user_by_username(self, username: str) -> User | None:
        # get user from username
        user = (await self.session.execute(
            select(User).where(User.username == username)
        )).scalars().first()
        return user if (user is not None) else None

    async def get_user_by_id(self, user_id: int) -> User | None:
        # get user from id
        user = (await self.session.execute(
            select(User).where(User.id == user_id)
        )).scalars().first()
        return user if (user is not None) else None

    async def get_user_by_im_id(self, im_id: int) -> User | None:
        # get user from IM user id
        user = (await self.session.execute(
            select(User).where(User.im_id == im_id)
        )).scalars().first()
        return user if (user is not None) else None

    async def get_player_count(self) -> int:
        return (
            await self.session.execute(
                select(func.count()).select_from(User)
            )
        ).scalars().first()

    async def get_client_by_token(self, token: str) -> Client | None:
        return (await self.session.execute(
            select(Client).where(Client.token == token)
        )).scalars().first()

    async def get_all_clients(self) -> list[Client]:
        return (await self.session.execute(
            select(Client)
        )).scalars().all()

    async def new_client(self, token: str, client_type: int, locale: str, mobile: bool, proxied: bool):
        client = Client(
            token=token,
            type=client_type,
            locale=locale,
            mobile=mobile,
            proxied=proxied,
            valid=True
        )
        self.session.add(client)
        await self.session.flush()

    async def revoke_client(self, client: Client):
        client.valid = False
        self.session.add(client)
        await self.session.flush()

    async def delete_client(self, client: Client):
        await self.session.delete(client)
        await self.session.flush()

    async def commit(self):
        await self.session.commit()