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

    if default and isinstance(default, bool):
        return True if value else False

    return value


class Config:
    ENABLE_DEBUG: bool = _load_from_environ('ENABLE_DEBUG', False)
    BOT_PREFIX: str = _load_from_environ('BOT_PREFIX', '%')
    QUART_HOST: str = _load_from_environ('QUART_HOST', '0.0.0.0')
    QUART_PORT: int = _load_from_environ('QUART_PORT', 9090)
    REDIS_URL: str = _load_from_environ('REDIS_URL', 'redis://:@localhost:6379/0')
    ENABLE_AUTORELOAD: bool = _load_from_environ('ENABLE_AUTORELOAD', False)
    QUART_AUTH_COOKIE_SECURE: bool = _load_from_environ('QUART_AUTH_COOKIE_SECURE', False)
    USE_DEFAULT_ERROR_HANDLER: bool = _load_from_environ('USE_DEFAULT_ERROR_HANDLER', True)
    VERBOSE_ERROR_MESSAGES: bool = _load_from_environ('VERBOSE_ERROR_MESSAGES', True)

    # Required Private Values
    BOT_TOKEN: str = _load_from_environ('BOT_TOKEN', None)
    SECRET_KEY: str = _load_from_environ('SECRET_KEY', _build_secret_key())

    _secret_attrs = ['BOT_TOKEN', 'SECRET_KEY']
