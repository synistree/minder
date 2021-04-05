from __future__ import annotations

import dateparser
import os
import os.path
import pytz
import logging

from dataclasses import dataclass, field
from datetime import datetime
from discord.ext import commands
from typing import Union, Optional, Mapping, Any, MutableMapping

from minder.config import Config
from minder.errors import MinderError

logger = logging.getLogger(__name__)


def validate_timezone(target_tz: str, throw_error: bool = False) -> bool:
    """
    Attempt to validate if the provided ``target_tz``

    Use this method to check if any provided timezone string value is in fact valid

    :param taret_tz: a timezone string such as ``America/Los_Angeles``
    """

    try:
        pytz.timezone(target_tz)
        return True
    except pytz.exceptions.UnknownTimeZoneError as ex:
        err_message = f'Invalid target timezone requested: "{target_tz}"'
        if throw_error:
            raise MinderError(err_message) from ex

        logger.warning(err_message)

        return False
    except pytz.exceptions.NonExistentTimeError as ex:
        err_message = f'Non-existent target timezone requested: "{target_tz}"'
        if throw_error:
            raise MinderError(err_message) from ex

        logger.warning(err_message)
        return False
    except Exception as ex:
        err_message = f'Generic error parsing timezone "{target_tz}": {ex}'

        if throw_error:
            raise MinderError(err_message) from ex

        logger.warning(err_message)
        return False
    else:
        err_message = f'Generic fall-through parsing timezone "{target_tz}" without an exception.'

        if throw_error:
            raise MinderError(err_message)

        logger.warning(err_message)
        return False


def format_datetime(source: datetime, target: Union[str, pytz.tzfile.DstTzInfo] = None, throw_error: bool = True) -> datetime:
    if not target:
        target = Config.USE_TIMEZONE or 'UTC'

    try:
        target_tz = pytz.timezone(target)
    except pytz.exceptions.UnknownTimeZoneError as ex:
        err_message = f'Invalid target timezone requested: "{target}"'
        if throw_error:
            raise MinderError(err_message) from ex

        logger.warning(err_message)
        return source
    except pytz.exceptions.NonExistentTimeError as ex:
        err_message = f'Non-existent target timezone requested: "{target}"'
        if throw_error:
            raise MinderError(err_message) from ex

        logger.warning(err_message)
        return source

    return source.astimezone(target_tz)


def get_working_path(use_working_path: str = None) -> str:
    working_path = os.path.expanduser(use_working_path or Config.WORKING_PATH)

    if not os.path.exists(working_path):
        logger.info(f'Creating new wrlibg path in "{working_path}"')
        os.makedirs(working_path)

    return working_path


@dataclass
class FuzzyTime:
    provided_when: str = field()

    created_time: datetime = field()
    resolved_time: datetime = field(init=False)

    @property
    def created_timestamp(self) -> float:
        return format_datetime(self.created_time).timestamp()

    @property
    def resolved_timestamp(self) -> float:
        return format_datetime(self.resolved_time).timestamp()

    @property
    def num_seconds_left(self) -> Optional[int]:
        dt_now = datetime.now()

        if dt_now > self.resolved_time:
            return None

        t_delta = (self.resolved_time - dt_now)

        return int(t_delta.total_seconds()) if t_delta else None

    def __post_init__(self) -> None:
        res_time = dateparser.parse(self.provided_when, settings={'PREFER_DATES_FROM': 'future'})
        if not res_time:
            raise ValueError(f'Unable to resolve provided "when": {self.provided_when}')

        self.resolved_time = res_time

    @classmethod
    def build(cls, provided_when: str, created_ts: Union[float, int, datetime] = None) -> FuzzyTime:
        kwargs: MutableMapping[str, Any] = {'provided_when': provided_when}

        if created_ts:
            kwargs['created_time'] = format_datetime(datetime.fromtimestamp(created_ts) if isinstance(created_ts, (int, float,)) else created_ts)

        return FuzzyTime(**kwargs)

    @classmethod
    def from_dict(cls, dict_mapping: Mapping[str, Any]) -> FuzzyTime:
        return FuzzyTime(provided_when=dict_mapping['provided_when'], created_time=dict_mapping.get('created_time', None))


class FuzzyTimeConverter(commands.Converter):
    async def convert(self, ctx, when: str):
        dt_now = datetime.now()
        try:
            fuz_time = FuzzyTime(when, created_time=dt_now)
        except ValueError as ex:
            await ctx.send(f'Sorry {ctx.author.mention}, provided fuzzy time `{when}` cannot be resolved :frowning: Try something like: `in 5 minutes`')
            raise commands.BadArgument(f'Unable to parse fuzzy time for "{ctx.author.name}": {ex}')

        return fuz_time
