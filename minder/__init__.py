import logging
import os
import os.path

from typing import TYPE_CHECKING

__version__ = '0.9.0'

LOG_LEVEL = logging.DEBUG

app_logger = logging.getLogger(__name__)
log_ch = logging.StreamHandler()


def setup_logger(log_level: int = logging.DEBUG, squelch: bool = False):
    log_fmt = logging.Formatter('[discoweb - %(levelname)s] %(asctime)s in %(module)s: %(message)s')
    log_ch.setFormatter(log_fmt)
    app_logger.setLevel(log_level)

    if not squelch:
        app_logger.addHandler(log_ch)
        app_logger.debug('Logging started for discoweb.')


setup_logger(log_level=LOG_LEVEL, squelch=TYPE_CHECKING)
