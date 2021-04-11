from __future__ import annotations

import dateparser
import discord
import os
import os.path
import pytz
import logging

try:
    from emoji import EMOJI_ALIAS_UNICODE as EMOJIS
except ImportError:
    # Found the OSX package at least needs the "_ENGLISH" suffix
    from emoji import EMOJI_ALIAS_UNICODE_ENGLISH as EMOJIS  # noqa: F401


from dataclasses import dataclass, field
from datetime import datetime, timedelta
from discord.ext import commands
from typing import Union, Optional, Any, MutableMapping, Mapping

from minder.config import Config
from minder.errors import MinderError, get_stacktrace
from minder.types import DateTimeType, TimezoneType

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


def format_datetime(source: datetime, target: TimezoneType = None, throw_error: bool = True) -> datetime:
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
class Timezone:
    timezone_name: str
    timezone: pytz.BaseTzInfo

    @property
    def utc_offset(self) -> timedelta:
        utc_tz = pytz.timezone('UTC')
        dt_now = datetime.now(utc_tz)

        return dt_now.astimezone(utc_tz).utcoffset()

    def format_datetime(self, value: datetime) -> datetime:
        # If tzinfo is available (i.e. non-native datetime) use normalize to
        # convert
        if value.tzinfo:
            return self.timezone.normalize(value)

        # Otherwise, use "datetime.astimezone" to convert
        return value.astimezone(self.timezone)

    def format_fuzzy(self, value: str, created_dt: datetime = None) -> FuzzyTime:
        created_dt = created_dt or datetime.now()
        return FuzzyTime.build(value, created_time=self.format_datetime(created_dt), use_timezone=self)

    @classmethod
    def is_valid_timezone(cls, timezone_name: str) -> bool:
        if not cls.get_timezone(timezone_name, throw_error=False):
            return False

        return True

    @classmethod
    def get_timezone(cls, timezone: TimezoneType, throw_error: bool = True) -> Optional[pytz.tzinfo.BaseTzInfo]:
        try:
            return pytz.timezone(timezone)
        except Exception as ex:
            if isinstance(ex, pytz.exceptions.InvalidTimeError):
                err_type = 'Invalid timezone'
            elif isinstance(ex, pytz.exceptions.NonExistentTimeError):
                err_type = 'Non-existent timezone'
            else:
                err_type = 'Generic'

            err_message = f'{err_type} error parsing "{timezone}"'

            if throw_error:
                raise MinderError(err_message) from ex

            logger.error(err_message)

            return None

    @classmethod
    def build(cls, timezone_name: str = None, throw_error: bool = True) -> Optional[Timezone]:
        timezone_name = timezone_name or 'UTC'
        tz = cls.get_timezone(timezone_name, throw_error=throw_error)
        if tz:
            return Timezone(timezone_name=timezone_name, timezone=tz)

        if not throw_error:
            logger.warning(f'Unable to build Timezone instance: Bad timezone name "{timezone_name}"')
            return None

        raise MinderError(f'Invalid timezone provided: "{timezone_name}"')

    def as_dict(self) -> Mapping[str, Any]:
        return {'timezone_name': self.timezone_name, 'timezone': self.timezone}


@dataclass
class FuzzyTime:
    provided_when: str = field()

    created_time: datetime = field(default_factory=datetime.now)
    resolved_time: datetime = field(init=False)

    use_timezone: Timezone = field(default_factory=lambda value: Timezone.build(value))

    @property
    def created_timestamp(self) -> float:
        create_dt = self.created_time

        if self.use_timezone and not self.created_time.tzinfo:
            create_dt = self.created_time.astimezone(self.use_timezone.timezone)

        return create_dt.timestamp()

    @property
    def resolved_timestamp(self) -> float:
        resolved_dt = self.resolved_time

        if self.use_timezone and not self.resolved_time.tzinfo:
            resolved_dt = resolved_dt.astimezone(self.use_timezone.timezone)

        return resolved_dt.timestamp()

    @property
    def num_seconds_left(self) -> Optional[int]:
        tz = self.use_timezone.timezone if self.use_timezone else pytz.utc
        dt_now = datetime.now().astimezone(tz)

        if dt_now > self.resolved_time:
            return None

        t_delta = (self.resolved_time - dt_now)

        return int(t_delta.total_seconds()) if t_delta else None

    def __post_init__(self) -> None:
        dp_settings = {'PREFER_DATES_FROM': 'future', 'RETURN_AS_TIMEZONE_AWARE': True}

        if self.use_timezone:
            dp_settings['TIMEZONE'] = self.use_timezone.timezone_name

        res_time = dateparser.parse(self.provided_when, settings=dp_settings)
        if not res_time:
            raise ValueError(f'Unable to resolve provided "when": {self.provided_when}')

        self.resolved_time = res_time

    @classmethod
    def build(cls, provided_when: str, created_time: DateTimeType = None,
              use_timezone: TimezoneType = None) -> FuzzyTime:
        if use_timezone:
            if isinstance(use_timezone, pytz.tzinfo.BaseTzInfo):
                timezone = use_timezone.zone
            elif isinstance(use_timezone, str):
                timezone = Timezone.build(use_timezone, throw_error=False)
                if not timezone:
                    raise MinderError(f'Invalid timezone provided: "{use_timezone}"')
            else:
                timezone = use_timezone
        else:
            timezone = Timezone.build()

        tz = timezone.timezone
        kwargs: MutableMapping[str, Any] = {'provided_when': provided_when, 'use_timezone': use_timezone}

        if created_time:
            if isinstance(created_time, (int, float,)):
                c_time = datetime.fromtimestamp(created_time, tz)
            else:
                c_time = created_time.astimezone(tz)

            kwargs['created_time'] = c_time

        return FuzzyTime(**kwargs)


class TimezoneConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, tz_name: str) -> Timezone:
        author = ctx.author.mention if ctx.author.guild else ctx.author.name
        new_tz = Timezone.build(tz_name, throw_error=False)

        if new_tz:
            return new_tz

        await ctx.send(f'Sorry {author}, invalid timezone "{tz_name}"')
        raise commands.BadArgument(f'Invalid timezone name "{tz_name}" when attempting to convert to a timezone')


class FuzzyTimeConverter(commands.Converter):
    timezone: Timezone
    created_time: datetime

    def __init__(self, *, timezone_name: str = None, created_time: datetime = None) -> None:
        timezone_name = timezone_name or 'utc'
        created_time = created_time or datetime.now()

        self.timezone = Timezone.build(timezone_name)
        self.created_time = created_time.astimezone(self.timezone.timezone)

    async def convert(self, ctx: commands.Context, when: str) -> FuzzyTime:
        author = ctx.author.mention if ctx.author.guild else ctx.author.name

        if not self.timezone:
            await ctx.send(f'Sorry {author}, provided timezone `{self.timezone_name}` is not valid')
            raise commands.BadArgument(f'Invalid timezone string "{self.timezone_name}" when converting fuzzy time string "{when}"')

        try:
            fuz_time = FuzzyTime.build(provided_when=when, created_time=self.created_time, use_timezone=self.timezone)
        except ValueError as ex:
            await ctx.send(f'Sorry {author}, provided fuzzy time `{when}` cannot be resolved :frowning: Try something like: `in 5 minutes`')
            raise commands.BadArgument(f'Unable to parse fuzzy time for "{ctx.author.name}": {ex}') from ex

        return fuz_time


def build_stacktrace_embed(from_exception: Exception = None) -> str:
    exc_out = get_stacktrace(from_exception)
    logger.debug(f'Reporting stack trace via embed:\n{exc_out}')

    return discord.Embed(title='Stack Trace', description=f'```python\n{exc_out}\n```')
