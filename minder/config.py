import os
import string
import random

from dotenv import load_dotenv

from typing import Any, Optional

env_path = os.environ.get('ENV_PATH', os.path.abspath(os.path.join(os.path.curdir, '.env')))

if not os.path.exists(env_path):
    raise Exception(f'No ".env" found in "{env_path} or ENV_PATH (if set)')

load_dotenv(env_path)


def _build_secret_key(length: int = 32, charset=string.ascii_letters + string.digits) -> str:
    return ''.join(random.choice(charset) for _ in range(length))


def _load_from_environ(name: str, default: Optional[Any]) -> Any:
    if name not in os.environ:
        if default is None:
            raise ValueError(f'Cannot find required config value in environ for "{name}". Cannot continue.')

        return default

    value = os.environ[name]

    if default is not None and isinstance(default, bool):
        return True if value else False

    return value


class Config:
    ENABLE_DEBUG: bool = _load_from_environ('ENABLE_DEBUG', False)
    BOT_PREFIX: str = _load_from_environ('BOT_PREFIX', '%')
    FLASK_HOST: str = _load_from_environ('FLASK_HOST', '0.0.0.0')
    FLASK_PORT: int = _load_from_environ('FLASK_PORT', 9090)
    REDIS_URL: str = _load_from_environ('REDIS_URL', 'redis://:@localhost:6379/0')
    ENABLE_AUTORELOAD: bool = _load_from_environ('ENABLE_AUTORELOAD', False)
    DEBUG_TB_ENABLED: bool = _load_from_environ('DEBUG_TB_ENABLED', False)
    USE_DEFAULT_ERROR_HANDLER: bool = _load_from_environ('USE_DEFAULT_ERROR_HANDLER', True)
    VERBOSE_ERROR_MESSAGES: bool = _load_from_environ('VERBOSE_ERROR_MESSAGES', True)
    USE_TIMEZONE: str = _load_from_environ('USE_TIMEZONE', 'UTC')
    SQLALCHEMY_ECHO: bool = _load_from_environ('SQLALCHEMY_ECHO', False)
    DEFAULT_CHECK_INTERVAL: int = _load_from_environ('DEFAULT_CHECK_INTERVAL', 10)
    SYNC_SLASH_COMMANDS: bool = _load_from_environ('SYNC_SLASH_COMMANDS', True)

    # Required Private Values
    BOT_TOKEN: str = _load_from_environ('BOT_TOKEN', None)
    SECRET_KEY: str = _load_from_environ('SECRET_KEY', _build_secret_key())
    SQLALCHEMY_URI: str = _load_from_environ('SQLALCHEMY_URI', None)
    SQLALCHEMY_DATABASE_URI: str = _load_from_environ('SQLALCHEMY_DATABASE_URI', _load_from_environ('SQLALCHEMY_URI', None))

    _secret_attrs = ['BOT_TOKEN', 'SECRET_KEY', 'SQLALCHEMY_URI', 'SQLALCHEMY_DATABASE_URI']
