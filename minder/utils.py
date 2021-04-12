from __future__ import annotations

import dateparser
import discord
import emoji
import pytz
import logging

# Found the OSX package at least needs the "_ENGLISH" suffix
if 'EMOJI_ALIAS_UNICODE' in dir(emoji):
    EMOJIS = getattr(emoji, 'EMOJI_ALIAS_UNICODE')
else:
    EMOJIS = getattr(emoji, 'EMOJI_ALIAS_UNICODE_ENGLISH')

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from discord.ext import commands
from typing import Optional, Any, MutableMapping, Mapping, Union
from pytz.exceptions import NonExistentTimeError, UnknownTimeZoneError, InvalidTimeError

from minder.errors import MinderError
from minder.common import DateTimeType

logger = logging.getLogger(__name__)
TimezoneType = Union[pytz.BaseTzInfo, 'Timezone', str]


@dataclass
class Timezone:
    timezone_name: str
    timezone: pytz.BaseTzInfo

    @classmethod
    def get_tz_error_type(cls, exception: Exception) -> str:
        if isinstance(exception, InvalidTimeError):
            return 'Invalid timezone'
        elif isinstance(exception, NonExistentTimeError):
            return 'Non-existent timezone'
        elif isinstance(exception, UnknownTimeZoneError):
            return 'Unknown timezone'

        return 'Generic'

    @property
    def utc_offset(self) -> Optional[timedelta]:
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
        try:
            cls.get_timezone(timezone_name)
        except Exception:
            return False

        return True

    @classmethod
    def get_timezone(cls, timezone_name: str) -> pytz.BaseTzInfo:
        try:
            return pytz.timezone(timezone_name)
        except Exception as ex:
            err_type = cls.get_tz_error_type(ex)
            err_message = f'{err_type} error parsing "{timezone_name}"'
            raise MinderError(err_message, base_exception=ex) from ex

    @classmethod
    def build(cls, timezone_name: str = None) -> Timezone:
        timezone_name = timezone_name or 'UTC'
        tz = cls.get_timezone(timezone_name)
        return Timezone(timezone_name=timezone_name, timezone=tz)

    def as_dict(self) -> Mapping[str, Any]:
        return {'timezone_name': self.timezone_name, 'timezone': self.timezone}


@dataclass
class FuzzyTime:
    provided_when: str = field()

    created_time: datetime = field(default_factory=datetime.now)
    resolved_time: datetime = field(init=False)

    use_timezone: Timezone = field(default_factory=Timezone.build)

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
            if isinstance(use_timezone, pytz.BaseTzInfo):
                timezone = Timezone(timezone_name=use_timezone.zone, timezone=use_timezone)
            elif isinstance(use_timezone, str):
                if not Timezone.is_valid_timezone(use_timezone):
                    raise MinderError(f'Invalid timezone provided: "{use_timezone}"')

                timezone = Timezone.build(use_timezone)
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

        if not Timezone.is_valid_timezone(tz_name):
            await ctx.send(f'Sorry {author}, invalid timezone "{tz_name}"')
            raise commands.BadArgument(f'Invalid timezone name "{tz_name}" when attempting to convert to a timezone')

        return Timezone.build(tz_name)


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
