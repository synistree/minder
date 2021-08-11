import os
import os.path
import ssl
import string
import random
import logging

from dotenv import load_dotenv
from typing import Any, Optional

from minder.errors import MinderError


logger = logging.getLogger(__name__)

env_path = os.environ.get('ENV_PATH', os.path.abspath(os.path.join(os.path.curdir, '.env')))

if not os.path.exists(env_path):
    if os.environ.get('SKIP_DOTENV', None):
        logger.info('Skipping load of dotenv config based on SKIP_DOTENV beingset')
    else:
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
    BOT_CONFIG_YAML: str = _load_from_environ('BOT_CONFIG_YAML', None)
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
    EXPLAIN_TEMPLATE_LOADING: bool = _load_from_environ('EXPLAIN_TEMPLATE_LOADING', False)
    ENABLE_BOT_JSONAPI: bool = _load_from_environ('ENABLE_BOT_JSONAPI', True)
    BOT_WEB_HOST: str = _load_from_environ('BOT_WEB_HOST', _load_from_environ('FLASK_HOST', None))
    BOT_WEB_PORT: int = _load_from_environ('BOT_WEB_PORT', 9091)
    SSL_ENABLE: bool = _load_from_environ('SSL_ENABLE', False)
    SSL_CAFILE: str = _load_from_environ('SSL_CAFILE', None)
    SSL_CERT: str = _load_from_environ('SSL_CERT', None)
    SSL_KEY: str = _load_from_environ('SSL_KEY', None)

    # Required Private Values
    BOT_TOKEN: str = _load_from_environ('BOT_TOKEN', None)
    SECRET_KEY: str = _load_from_environ('SECRET_KEY', _build_secret_key())
    SQLALCHEMY_URI: str = _load_from_environ('SQLALCHEMY_URI', None)
    SQLALCHEMY_DATABASE_URI: str = _load_from_environ('SQLALCHEMY_DATABASE_URI', _load_from_environ('SQLALCHEMY_URI', None))
    BOT_SQLALCHEMY_URI: str = _load_from_environ('BOT_SQLALCHEMY_URI', None)

    _secret_attrs = ['BOT_TOKEN', 'SECRET_KEY', 'SQLALCHEMY_URI', 'SQLALCHEMY_DATABASE_URI', 'BOT_SQLALCHEMY_URI']

    @classmethod
    def get_ssl_context(cls, ignore_error: bool = False) -> Optional[ssl.SSLContext]:
        if not cls.SSL_ENABLE:
            return None

        for name in ['SSL_CAFILE', 'SSL_CERT', 'SSL_KEY']:
            cfg_file = getattr(cls, name, None)

            if not cfg_file:
                msg = f'SSL_ENABLE is set but no config found for "{cfg_file}"'

                if not ignore_error:
                    raise MinderError(msg)

                logger.warning(f'{msg}. Ignoring based on arguments and using HTTP')

            if not os.path.exists(cfg_file) or not os.path.stat(cfg_file):
                msg = f'SSL_ENABLE is set but cannot find "{name}" file in "{cfg_file}": Path does not exist or is unreadable'

                if not ignore_error:
                    raise MinderError(msg)

                logger.warning(f'{msg}. Ignoring based on arguments and using HTTP')

        ssl_ctx = ssl.create_default_context(cafile=Config.SSL_CAFILE)
        ssl_ctx.load_cert_chain(certfile=cls.SSL_CERT, keyfile=cls.SSL_KEY)

        return ssl_ctx
