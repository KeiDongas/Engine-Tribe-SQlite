import os
import yaml

def deep_update(config, override_config):
    for key, value in override_config.items():
        if isinstance(value, dict):
            config[key] = deep_update(config.get(key, {}), value)
        else:
            config[key] = value
    return config

config_path = os.getenv("ENGINETRIBE_CONFIG_PATH", "config.yml")

if os.path.exists("config.default.yml"):
    _config = yaml.safe_load(open("config.default.yml", "r"))
    _override_config = yaml.safe_load(open(config_path, "r"))
    _config = deep_update(_config, _override_config)
else:
    _config = yaml.safe_load(open(config_path, "r"))

# Engine Tribe Configurations
HOST = _config["enginetribe"]["host"]
PORT = _config["enginetribe"]["port"]
API_ROOT = _config["enginetribe"]["api_root"]
WORKERS = _config["enginetribe"]["workers"]
VERIFY_USER_AGENT = _config["enginetribe"]["verify_user_agent"]
API_KEY = _config["enginetribe"]["api_key"]
ROWS_PERPAGE = _config["enginetribe"]["rows_perpage"]
UPLOAD_LIMIT = _config["enginetribe"]["upload_limit"]
BOOSTERS_EXTRA_LIMIT = _config["enginetribe"]["booster_extra_limit"]
RECORD_CLEAR_USERS = _config["enginetribe"]["record_clear_users"]
CORS_ALLOWED_ORIGINS = _config["enginetribe"]["cors_allowed_origins"]

# Database Configurations
DATABASE_ADAPTER = _config['database']['adapter']
DATABASE_HOST = _config['database']['host']
DATABASE_PORT = _config['database']['port']
DATABASE_USER = _config['database']['user']
DATABASE_PASS = _config['database']['password']
DATABASE_NAME = _config['database']['database']
DATABASE_SSL = _config['database']['ssl']
DATABASE_DEBUG = _config['database']['debug']
USERS_DB_PATH = _config['database']['users_db_path']
LEVELS_DB_PATH = _config['database']['levels_db_path']

# Construct the full database URL based on the adapter
if DATABASE_ADAPTER == 'sqlite':
    # This is the line to fix.
    # The URL needs to specify the aiosqlite driver for async support.
    USERS_DATABASE_URL = f'sqlite+aiosqlite:///./users.db'
    LEVELS_DATABASE_URL = f'sqlite+aiosqlite:///./levels.db'
elif DATABASE_ADAPTER == 'postgresql':
    DATABASE_URL = f'postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASS}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}'
elif DATABASE_ADAPTER == 'mysql':
    DATABASE_URL = f'mysql+aiomysql://{DATABASE_USER}:{DATABASE_PASS}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}'
else:
    raise ValueError(f'Unsupported database adapter: {DATABASE_ADAPTER}')

# Redis Configurations
SESSION_REDIS_HOST = _config['redis']['host']
SESSION_REDIS_PORT = _config['redis']['port']
SESSION_REDIS_DB = _config['redis']['database']
SESSION_REDIS_PASS = _config['redis']['password']

# Storage Configurations
STORAGE_PROVIDER = _config['storage']['provider']
STORAGE_URL = _config['storage']['url']
STORAGE_AUTH_KEY = _config['storage']['auth_key']
STORAGE_PROXIED = _config['storage']['proxied']
STORAGE_ATTACHMENT_CHANNEL_ID = _config['storage']['attachment_channel_id']

# Push Configurations (Engine Bot)
ENABLE_ENGINE_BOT_WEBHOOK = _config['push']['engine_bot']['enabled']
ENABLE_ENGINE_BOT_COUNTER_WEBHOOK = _config['push']['engine_bot']['enable_counter']
ENABLE_ENGINE_BOT_ARRIVAL_WEBHOOK = _config['push']['engine_bot']['enable_new_arrival']
ENGINE_BOT_WEBHOOK_URLS = _config['push']['engine_bot']['urls']

# Push Configurations (Discord)
ENABLE_DISCORD_WEBHOOK = _config['push']['discord']['enabled']
ENABLE_DISCORD_ARRIVAL_WEBHOOK = _config['push']['discord']['enable_new_arrival']
DISCORD_WEBHOOK_URLS = _config['push']['discord']['urls']
DISCORD_AVATAR_URL = _config['push']['discord']['avatar']
DISCORD_NICKNAME = _config['push']['discord']['nickname']
DISCORD_SERVER_NAME = _config['push']['discord']['server_name']