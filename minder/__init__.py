import logging
import os
import os.path

from logging.config import dictConfig

__version__ = '0.10.1'

DEFAULT_LOG_LEVEL = os.environ.get('LOG_LEVEL', logging.INFO)
LOG_LEVEL = logging.DEBUG if os.environ.get('DEBUG', False) else logging.INFO

cfmt_timestamp = '%(green)s%(asctime)s %(cyan)s%(levelname)s%(reset)s'
cfmt_module = '%(red)s%(name)s%(reset)s::%(blue)s%(module)s%(reset)s'
cfmt_func = '%(green)s%(funcName)s%(reset)s(%(cyan)s%(args)s%(reset)s'
color_fmt = f'[{cfmt_timestamp}] [{cfmt_module}]: %(message)s'

dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'colored': {
            '()': 'colorlog.ColoredFormatter',
            'format': color_fmt,
            'datefmt': "%H:%M:%S"
        }
    },
    'handlers': {
       'stream': {
           'class': 'logging.StreamHandler',
           'formatter': 'colored'
        }
    },
    'loggers': {
        'minder': {
            'level': LOG_LEVEL
        },
        'discord': {
            'level': logging.INFO if os.environ.get('DEBUG', False) else logging.WARNING
        },
        '': {
            'handlers': ['stream'],
            'level': DEFAULT_LOG_LEVEL
        }
    }
})

app_logger = logging.getLogger(__name__)
