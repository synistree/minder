from __future__ import annotations

import dateparser
import logging

from dataclasses import dataclass, field
from datetime import datetime
from discord.ext import commands
from typing import Union, Optional, Mapping, Any, MutableMapping

logger = logging.getLogger(__name__)


@dataclass
class FuzzyTime:
    provided_when: str = field()

    created_time: datetime = field()
    resolved_time: datetime = field(init=False)

    @property
    def created_timestamp(self) -> float:
        return self.created_time.timestamp()

    @property
    def resolved_timestamp(self) -> float:
        return self.resolved_time.timestamp()

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
            kwargs['created_time'] = datetime.fromtimestamp(created_ts) if isinstance(created_ts, (int, float,)) else created_ts

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
