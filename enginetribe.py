#!/usr/bin/env python3

import datetime
import platform
import uvicorn
from fastapi import (
    FastAPI, Request, status, Depends
)
from fastapi.responses import (
    RedirectResponse, JSONResponse, FileResponse, Response
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from redis import asyncio as redis
import asyncio
import aiohttp

# Importa ambas clases de la capa de acceso a datos

from database.users_db_access import UsersDBAccessLayer
from database.levels_db_access import LevelsDBAccessLayer
import routers
from config import *
from models import ErrorMessageException
import push
from database.db import Database
from storage.onedrive_cf import StorageProviderOneDriveCF
from storage.onemanager import StorageProviderOneManager
from storage.database import StorageProviderDatabase
from storage.discord import StorageProviderDiscord


# Dependencia para obtener la capa de acceso a datos de los usuarios.
def create_users_dal(request: Request) -> UsersDBAccessLayer:
    return UsersDBAccessLayer(request.app.state.users_db.async_session())

# Dependencia para obtener la capa de acceso a datos de los niveles.
def create_levels_dal(request: Request) -> LevelsDBAccessLayer:
    return LevelsDBAccessLayer(request.app.state.levels_db.async_session())


async def connection_per_minute_record():
    await asyncio.sleep(60)
    app.state.connection_per_minute = app.state.connection_count
    app.state.connection_count = 0
    asyncio.create_task(connection_per_minute_record())


app = FastAPI(
    redoc_url="",
    docs_url="/interactive_docs",
)

app.include_router(routers.stage.router)
app.include_router(routers.user.router)
app.include_router(routers.client.router)

# La inicialización de la base de datos se mueve al evento de inicio
# para asegurar que se crea el motor de forma asíncrona.
# Es importante eliminar cualquier código de inicialización de DB aquí.


app.mount("/web", StaticFiles(directory="web", html=True), name="web")


@app.get("/favicon.ico")
async def favicon_handler() -> FileResponse:
    return FileResponse("web/favicon.ico")


_static_file_mimes: dict[str, str] = {}
_static_file_cache: dict[str, bytes] = {}


@app.get("/static/{filename}")
async def static_file_proxy(filename: str) -> Response:
    if filename not in _static_file_cache:
        async with aiohttp.request(
                method="GET",
                url=f"http://www.enginetribe.gq/static/{filename}"
        ) as response:
            if response.status != 200:
                return Response(status_code=404)
            _static_file_mimes[filename] = response.content_type
            _static_file_cache[filename] = await response.read()
    return Response(
        content=_static_file_cache[filename],
        media_type=_static_file_mimes[filename]
    )


@app.get("/")
async def readme_handler() -> FileResponse:
    return FileResponse("web/index.html")


@app.get("/docs")
async def docs_handler() -> RedirectResponse:
    return RedirectResponse("http://www.enginetribe.gq/docs")


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

start_time = datetime.datetime.now()


@app.on_event("startup")
async def startup_event():
    # Se crean las instancias de la clase Database
    app.state.users_db = Database(
        db_url=USERS_DATABASE_URL,
        db_debug=DATABASE_DEBUG,
        db_ssl=DATABASE_SSL
    )
    app.state.levels_db = Database(
        db_url="sqlite+aiosqlite:///levels.db"
    )
    
    # Se crean las tablas para ambas bases de datos.
    await app.state.users_db.create_all_tables()
    await app.state.levels_db.create_all_tables()
    
    app.state.connection_count = 0
    app.state.storage = {
        "onedrive-cf": StorageProviderOneDriveCF(
            url=STORAGE_URL, auth_key=STORAGE_AUTH_KEY, proxied=STORAGE_PROXIED
        ),
        "onemanager": StorageProviderOneManager(
            url=STORAGE_URL, admin_password=STORAGE_AUTH_KEY
        ),
        "database": StorageProviderDatabase(
            base_url=API_ROOT,
            database=app.state.levels_db
        ),
        "discord": StorageProviderDiscord(
            api_url=STORAGE_URL,
            base_url=API_ROOT,
            database=app.state.levels_db,
            attachment_channel=STORAGE_ATTACHMENT_CHANNEL_ID
        )
    }[STORAGE_PROVIDER]
    app.state.redis = redis.Redis(
        connection_pool=redis.ConnectionPool(
            host=SESSION_REDIS_HOST,
            port=SESSION_REDIS_PORT,
            db=SESSION_REDIS_DB,
            password=SESSION_REDIS_PASS
        )
    )
    app.state.connection_count = 0
    app.state.connection_per_minute = 0
    asyncio.create_task(connection_per_minute_record())
    asyncio.create_task(push.push_to_engine_bot_sub())
    asyncio.create_task(push.push_to_engine_bot_discord_sub())


@app.on_event("shutdown")
async def shutdown_event():
    await app.state.redis.flushdb()
    await app.state.redis.close()
    # Se cierran las conexiones de ambas bases de datos al apagar la aplicación
    # Asegúrate de que los métodos dispose() existen en tu clase Database.
    await app.state.users_db.engine.dispose()
    await app.state.levels_db.engine.dispose()


# get server stats
@app.get("/server_stats")
async def server_stats(
    users_dal: UsersDBAccessLayer = Depends(create_users_dal),
    levels_dal: LevelsDBAccessLayer = Depends(create_levels_dal)
) -> dict:
    return {
        "os": platform.platform().replace('-', ' '),
        "python": platform.python_version(),
        # Se obtiene el conteo de jugadores desde la base de datos de usuarios
        "player_count": await users_dal.get_player_count(),
        # Se obtiene el conteo de niveles desde la base de datos de niveles
        "level_count": await levels_dal.get_level_count(),
        "uptime": (datetime.datetime.now() - start_time).seconds,
        "connection_per_minute": app.state.connection_per_minute,
    }


@app.exception_handler(ErrorMessageException)
async def error_message_exception_handler(request: Request, exc: ErrorMessageException):
    return JSONResponse(
        status_code=200,
        content={
            "error_type": exc.error_type,
            "message": exc.message,
        },
    )


@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def route_not_found_handler(request: Request, exc: ErrorMessageException):
    return JSONResponse(
        status_code=404,
        content={
            "error_type": "001",
            "message": "Route not found.",
        },
    )


def run():
    uvicorn.run(
        app=app,
        host=HOST,
        port=PORT,
        workers=WORKERS,
        headers=[
            ("Server", "EngineTribe"),
            ("X-Powered-By", "EngineTribe"),
        ]
    )


if __name__ == "__main__":
    run()