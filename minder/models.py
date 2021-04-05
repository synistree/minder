from __future__ import annotations

import discord
import humanize

from dataclasses import dataclass, field
from datetime import datetime
from redisent.models import RedisEntry
from typing import Union, Optional, Mapping, Any

from minder.errors import MinderError
from minder.utils import FuzzyTime


@dataclass
class UserSettings(RedisEntry):
    redis_id: str = 'user_settings'

    guild_id: int = field(default_factory=int)
    member_id: int = field(default_factory=int)

    settings: Mapping[str, Any] = field(default_factory=dict)
    default_settings: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.redis_name = f'{self.guild_id}:{self.member_id}'

    def get_value(self, setting_name: str, throw_error: bool = True) -> Optional[str]:
        if setting_name in self.settings:
            return self.settings[setting_name]

        if setting_name in self.default_settings:
            return self.default_settings[setting_name]

        if throw_error:
            raise MinderError(f'Invalid user setting value requested: "{setting_name}"')

        return None


@dataclass
class Reminder(RedisEntry):
    redis_id: str = 'reminders'
    member_id: int = field(default_factory=int)
    member_name: str = field(default_factory=str)

    channel_id: int = field(default_factory=int)
    channel_name: str = field(default_factory=str)

    provided_when: str = field(default_factory=str)
    content: str = field(default_factory=str)

    trigger_ts: float = field(default_factory=float)
    created_ts: float = field(default_factory=float)

    user_notified: bool = field(default=False, compare=False)
    trigger_time: FuzzyTime = field(init=False)

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
        self.redis_name = f'{self.member_id}:{self.trigger_ts}'
        self.trigger_time = FuzzyTime.build(self.provided_when, created_ts=self.created_ts)

    @classmethod
    def build(cls, trigger_time: FuzzyTime, member: discord.Member, channel: discord.TextChannel, content: str) -> Reminder:
        return Reminder(created_ts=trigger_time.created_timestamp, trigger_ts=trigger_time.resolved_timestamp, member_id=member.id, member_name=member.name,
                        channel_id=channel.id, channel_name=channel.name, provided_when=trigger_time.provided_when, content=content)

    def as_markdown(self, author: discord.Member = None, channel: discord.TextChannel = None,
                    as_embed: Union[discord.Embed, bool] = False) -> Union[discord.Embed, str]:
        member_str = author.mention or self.member_name
        channel_str = channel.mention or self.channel_name
        emb_content = self.content if '```' in self.content else f'```{self.content}```'

        created_dt = self.trigger_time.created_time
        trigger_dt = self.trigger_time.resolved_time

        if self.is_complete:
            time_left = 'N/A'
            out_prefix = 'Complete Reminder'
        else:
            time_left = humanize.naturaltime(self.trigger_time.num_seconds_left, future=True)
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
