from __future__ import annotations

import discord
import humanize
import logging

from datetime import datetime
from redisent.models import RedisEntry
from typing import Mapping, Union, Optional

from minder.common import MemberType, ChannelType, AnyMemberType, AnyChannelType
from minder.errors import MinderError
from minder.utils import FuzzyTime, Timezone

from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Reminder(RedisEntry):
    redis_id: str = 'reminders'

    member_id: int = field(default_factory=int)
    member_name: str = field(default_factory=str)

    provided_when: str = field(default_factory=str)
    content: str = field(default_factory=str)

    trigger_ts: float = field(default_factory=float)
    created_ts: float = field(default_factory=float)

    user_notified: bool = field(default=False, compare=False)
    trigger_time: FuzzyTime = field(init=False)

    from_dm: Optional[bool] = field(default_factory=bool)
    timezone_name: str = field(default='UTC')

    channel_id: Optional[int] = field(default_factory=int)
    channel_name: Optional[str] = field(default_factory=str)

    @property
    def timezone(self) -> Timezone:
        return Timezone.build(self.timezone_name)

    @property
    def trigger_dt(self) -> datetime:
        """
        Property wrapper for converting the float "trigger_ts" into "datetime"
        """

        return datetime.fromtimestamp(self.trigger_ts)

    @property
    def created_dt(self) -> datetime:
        """
        Property wrapper for converting the float "created_ts" into "datetime"
        """

        return datetime.fromtimestamp(self.created_ts)

    @property
    def is_complete(self) -> bool:
        dt_now = datetime.now()

        return self.trigger_dt < dt_now

    def __post_init__(self) -> None:
        self.redis_id = 'reminders'

        if not self.timezone_name:
            logger.warning(f'No timezone setting found for "{self.redis_name}". Setting to "UTC"')
            self.timezone_name = 'UTC'

        if not self.redis_name:
            self.redis_name = f'{self.member_id}:{self.trigger_ts}'

        # TODO: This really does not need to be stored in Redis. Instead we should only store the timestamp and use the
        # timezone info from the reminder entry class
        self.trigger_time = FuzzyTime.build(self.provided_when, created_time=self.created_ts, use_timezone=self.timezone)

        if self.from_dm is None:
            self.from_dm = True if not self.channel_id or not self.channel_name else False

    @classmethod
    def build(cls, trigger_time: Union[FuzzyTime, str], member: AnyMemberType, content: str, channel: AnyChannelType = None,
              created_at: datetime = None, use_timezone: Union[str, Timezone] = None) -> Reminder:
        member_id, member_name = None, None
        channel_id, channel_name = None, None
        from_dm = False
        target_tz: Optional[Timezone] = None

        if use_timezone:
            if isinstance(use_timezone, str):
                if not Timezone.is_valid_timezone(use_timezone):
                    raise MinderError(f'Invalid timezone provided: "{use_timezone}"')

                target_tz = Timezone.build(timezone_name=use_timezone)
            else:
                target_tz = use_timezone

        if isinstance(member, Mapping):
            member_id = int(member['id'])
            member_name = member['name']
        else:
            member_id = member.id
            member_name = member.name

        if channel:
            if isinstance(channel, discord.abc.Messageable):
                channel_id = channel.id

                if isinstance(channel, discord.DMChannel):
                    channel_name = f'DM {member_name}'
                    from_dm = True
                else:
                    channel_name = channel.name
            else:
                channel_id = channel['id']
                channel_name = channel['name']

        if not isinstance(trigger_time, FuzzyTime):
            trigger_time = FuzzyTime.build(provided_when=trigger_time, created_time=created_at, use_timezone=target_tz)

        created_ts = trigger_time.created_timestamp
        trigger_ts = trigger_time.resolved_timestamp
        provided_when = trigger_time.provided_when
        tz_name = target_tz.timezone_name if target_tz else 'UTC'

        return Reminder(created_ts=created_ts, trigger_ts=trigger_ts, member_id=member_id, member_name=member_name,
                        channel_id=channel_id, channel_name=channel_name, provided_when=provided_when, content=content,
                        from_dm=from_dm, timezone_name=tz_name)

    def as_markdown(self, author: MemberType = None, channel: Union[ChannelType, discord.abc.GuildChannel] = None,
                    as_embed: Union[discord.Embed, bool] = False) -> Union[discord.Embed, str]:
        channel_str = self.channel_name
        member_str = self.member_name

        if channel:
            channel_str = channel.recipient.name if isinstance(channel, discord.DMChannel) else channel.mention

        if author:
            member_str = author.mention

        emb_content = self.content if '```' in self.content else f'```{self.content}```'

        created_dt = self.trigger_time.created_time
        trigger_dt = self.trigger_time.resolved_time

        if self.is_complete:
            time_left = 'N/A'
            out_prefix = 'Complete Reminder'
        else:
            time_left = humanize.naturaldelta(self.trigger_time.num_seconds_left, months=False)
            out_prefix = 'Pending Reminder'

        if as_embed:
            if isinstance(as_embed, discord.Embed):
                emb = as_embed
            else:
                emb = discord.Embed(title=f'{out_prefix} for "{self.member_name}" @ `{trigger_dt.ctime()}`',
                                    description=f'Reminder for {member_str} as requested at `{created_dt.ctime()}` in {channel_str} :wink:',
                                    color=discord.Color.dark_grey())

            emb.add_field(name='Remind At', value=f'`{trigger_dt.ctime()}` (based on `{self.trigger_time.provided_when or "N/A"}`)', inline=False)
            emb.add_field(name='Amount of time left', value=f'`{time_left}`', inline=False)
            emb.add_field(name='Timezone', value=f'`{self.timezone_name}`', inline=False)
            emb.add_field(name='Requested At', value=f'`{created_dt.ctime()}`', inline=False)

            emb.add_field(name='Reminder Content', value=emb_content, inline=False)

            emb.set_footer(text=f'Bot reminder for "{self.member_name}" for "{trigger_dt.ctime()}"')

            return emb

        out_lines = [f'{out_prefix} for {member_str} at `{trigger_dt.ctime()}`:']
        out_lines += [f'> Requested At: `{created_dt.ctime()}`',
                      f'> Requested "when": `{self.trigger_time.provided_when or "Unknown"}`',
                      f'> Amount of time left: `{time_left}`',
                      f'> Created In: {channel_str}',
                      emb_content]

        return '\n'.join(out_lines)
