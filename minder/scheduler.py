from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from typing import Callable

from minder.config import Config

logger = logging.getLogger(__name__)


def build_scheduler(callback_handler: Callable[[], []], interval: int = None,
                    start_scheduler: bool = True) -> BackgroundScheduler:
    """
    Method for building a new :py:cls:`BackgroundScheduler` that will monitor reminder events and dispatch accordingly

    This method will also register a new scheduler job that will fire at the provided interval or default to using the
    :py:attr:`Config.DEFAULT_CHECK_INTERVAL` value.

    :param callback_handler: callable that takes no arguments and returns no value. this will be during each run of
                             the scheduled job (i.e. at each ``interval``)
    :param interval: the interval at which the scheduled job should be called (in seconds). if not provided, the
                     default value from :py:attr:`Config.DEFAULT_CHECK_INTERVAL` will be used.
    :param start_scheduler: if set, the scheduler will be immediately started
    """

    interval = int(interval or Config.DEFAULT_CHECK_INTERVAL)
    target_tz = Config.USE_TIMEZONE or 'UTC'

    scheduler = BackgroundScheduler({'apscheduler.timezone': target_tz})

    scheduler.add_job(callback_handler, trigger='interval', seconds=interval)

    if start_scheduler:
        logger.info(f'Starting new scheduler..')
        scheduler.start()

    return scheduler
