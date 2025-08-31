from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    AsyncAttrs,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase
import ssl
from typing import Optional

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Database:
    def __init__(self, db_url: str, db_debug: bool = False, db_ssl: bool = False):
        url: str = db_url

        connect_args = {}
        if db_ssl:
            ssl_ctx = ssl.create_default_context(cafile="/etc/ssl/certs/ca-certificates.crt")
            ssl_ctx.verify_mode = ssl.CERT_REQUIRED
            connect_args['ssl'] = ssl_ctx
        
        self.engine: AsyncEngine = create_async_engine(
            url=url,
            echo=db_debug,
            future=True,
            connect_args=connect_args
        )

        self.async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine,
            expire_on_commit=False
        )

    async def create_all_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)