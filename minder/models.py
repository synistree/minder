from __future__ import annotations

import discord
import humanize
import os.path
import yaml

from dataclasses import dataclass, field
from datetime import datetime
from redisent.models import RedisEntry
from typing import Union, Optional, Mapping, Any

from minder.errors import MinderError
from minder.utils import FuzzyTime


@dataclass
class UserSettings(RedisEntry):
    redis_id: str = 'user_settings'

    guild_id: Optional[int] = field(default=None)
    member_id: int = field(default_factory=int)

    settings: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.redis_name = self.member_id

    def set_value(self, name: str, value: Any) -> bool:
        has_value = True if self.has_setting(name) else False
        self.settings[name] = value
        return has_value

    def has_setting(self, name: str) -> bool:
        return name in self.settings

    def get_value(self, name: str, throw_error: bool = True, **kwargs) -> Optional[Any]:
        if self.has_setting(name):
            return self.settings[name]

        if 'default' in kwargs:
            return kwargs['default']

        if throw_error:
            raise MinderError(f'Invalid user setting value requested: "{name}"')

        return None

    @classmethod
    def from_yaml(cls, yaml_file: str) -> UserSettings:
        yaml_file = os.path.abspath(os.path.expanduser(yaml_file))

        if not os.path.exists(yaml_file):
            raise MinderError(f'Unable to find user settings file "{yaml_file}"')

        try:
            with open(yaml_file, 'rt') as f:
                yaml_cfg = yaml.safe_load(f)
        except Exception as ex:
            raise MinderError(f'Failure parsing user settings from "{yaml_file}": {ex}') from ex

        member_id = yaml_cfg['member_id']
        guild_id = yaml_cfg.get('guild_id', None)
        return UserSettings(guild_id=guild_id, member_id=member_id, settings=yaml_cfg['settings'])


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

    from_dm: Optional[bool] = field(default=None)

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
        self.trigger_time = FuzzyTime.build(self.provided_when, created_time=self.created_ts)

        if self.from_dm is None:
            self.from_dm = True if not self.channel_id or not self.channel_name else False

    @classmethod
    def build(cls, trigger_time: Union[FuzzyTime, str], member: discord.Member, content: str, channel: Union[discord.TextChannel, discord.DMChannel] = None,
              created_at: datetime = None) -> Reminder:
        channel_id, channel_name = None, None
        from_dm = False

        if channel:
            channel_id = channel.id

            if isinstance(channel, discord.DMChannel):
                channel_name = f'DM {member.name}'
                from_dm = True
            else:
                channel_name = channel.name

        if not isinstance(trigger_time, FuzzyTime):
            trigger_time = FuzzyTime.build(provided_when=trigger_time, created_time=created_at)

        created_ts = trigger_time.created_timestamp
        trigger_ts = trigger_time.resolved_timestamp
        provided_when = trigger_time.provided_when

        return Reminder(created_ts=created_ts, trigger_ts=trigger_ts, member_id=member.id, member_name=member.name,
                        channel_id=channel_id, channel_name=channel_name, provided_when=provided_when, content=content,
                        from_dm=from_dm)

    def as_markdown(self, author: Union[discord.User, discord.Member] = None, channel: Union[discord.TextChannel, discord.DMChannel] = None,
                    as_embed: Union[discord.Embed, bool] = False) -> Union[discord.Embed, str]:
        channel_str = self.channel_name
        member_str = self.member_name

        if channel:
            channel_str = channel.name if isinstance(channel, discord.DMChannel) else channel.mention

        if author:
            member_str = author.mention

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
