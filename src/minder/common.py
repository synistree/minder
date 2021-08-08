from __future__ import annotations

import discord
import logging

from dataclasses import dataclass, field, InitVar
from datetime import datetime
from discord.ext import commands
from typing import Any, Union, Optional, Mapping

from minder.errors import MinderBotError

logger = logging.getLogger(__name__)

DateTimeType = Union[float, int, datetime]
MemberType = Union[discord.Member, discord.User]
ChannelType = Union[discord.TextChannel, discord.DMChannel]
ContextOrGuildType = Union[discord.Guild, commands.Context]

AnyMemberType = Union[MemberType, Mapping[str, Any]]
AnyChannelType = Union[ChannelType, Mapping[str, Any]]


@dataclass
class DiscordGuild:
    id: int
    name: str


@dataclass
class DiscordMember:
    id: int = field()
    name: str = field()

    _guild: InitVar[discord.Guild] = field(default=None)
    _member: InitVar[MemberType] = field(default=None)

    @property
    def mention(self):
        return str(self._member.mention) if self._member else self.name

    @property
    def guild(self) -> Optional[discord.Guild]:
        if self._guild:
            return self._guild

        if not self._member or not isinstance(self._member, discord.Member):
            return None

        return self._member.guild

    @property
    def member(self) -> Optional[MemberType]:
        return self._member

    @classmethod
    def from_model(cls, member_or_user: discord.abc.Messageable) -> Optional[DiscordMember]:
        if not isinstance(member_or_user, (discord.Member, discord.User,)):
            return None

        guild = member_or_user.guild if isinstance(member_or_user, discord.Member) else None
        return DiscordMember(id=member_or_user.id, name=member_or_user.name, _guild=guild, _member=member_or_user)

    @classmethod
    def build(cls, id: int, name: str, context_or_guild: ContextOrGuildType = None) -> DiscordMember:
        if not context_or_guild:
            return DiscordMember(id=id, name=name)

        member = cls.resolve(id, context_or_guild)

        if isinstance(context_or_guild, commands.Context):
            guild = context_or_guild.guild

        return DiscordMember(id=id, name=name, _guild=guild, _member=member)

    @staticmethod
    def resolve(id: int, guild: Optional[ContextOrGuildType]) -> Optional[discord.Member]:
        if isinstance(guild, commands.Context):
            guild = guild.guild

        if guild is None:
            return None

        try:
            member = guild.get_member(id)
        except Exception as ex:
            if not isinstance(ex, discord.errors.NotFound):
                raise MinderBotError(f'General error lookup up member ID {id}: {ex}', base_exception=ex)

            logger.warning(f'No member found for ID {id} on guild "{guild.name}" (ID {guild.id}). Not resolving.')
            member = None

        return member


@dataclass
class DiscordChannel:
    id: int = field()
    name: str = field()

    is_dm: Optional[bool] = field(default=None, init=False)
    _guild: InitVar[discord.Guild] = field(default=None)
    _channel: InitVar[ChannelType] = field(default=None)

    @property
    def mention(self) -> str:
        if not self._channel or not isinstance(self._channel, discord.TextChannel):
            return self.name

        return self._channel.mention

    @property
    def guild(self) -> Optional[discord.Guild]:
        if self._guild:
            return self._guild

        if self._channel and not isinstance(self._channel, discord.DMChannel):
            return self._channel.guild

        return None

    @property
    def channel(self) -> Optional[ChannelType]:
        return self._channel

    @classmethod
    def from_model(cls, channel_or_dm: ChannelType) -> Optional[DiscordChannel]:
        if not isinstance(channel_or_dm, (discord.TextChannel, discord.DMChannel,)):
            return None

        guild = channel_or_dm.guild if isinstance(channel_or_dm, discord.TextChannel) else None
        chan_name = channel_or_dm.recipient.name if isinstance(channel_or_dm, discord.DMChannel) else channel_or_dm.name
        return DiscordChannel(id=channel_or_dm.id, name=chan_name, _guild=guild, _channel=channel_or_dm)

    @classmethod
    def build(cls, id: int, name: str, is_dm: bool = None, context_or_guild: ContextOrGuildType = None) -> DiscordChannel:
        guild, channel = None, None

        if not context_or_guild and not name:
            raise MinderBotError(f'No guild/context provided when looking up channel "{id}" with no provided username. Provide "name" explicitly')

        if context_or_guild:
            channel = cls.resolve(id, context_or_guild)

            if not name:
                if not channel:
                    ctx = context_or_guild if isinstance(context_or_guild, commands.Context) else None
                    raise MinderBotError(f'Failed to resolve channel ID {id} and no "name" provided.', context=ctx)

                name = channel.recipient.name if isinstance(channel, discord.DMChannel) else channel.name

        if is_dm is None and channel:
            is_dm = isinstance(channel, discord.DMChannel)

        return DiscordChannel(id=id, name=name, is_dm=is_dm, _guild=guild, _channel=channel)

    @staticmethod
    def resolve(id: int, guild: ContextOrGuildType) -> Optional[ChannelType]:
        if isinstance(guild, commands.Context):
            if not guild.guild:
                return None

            guild = guild.guild

        try:
            channel = guild.get_channel(id)
            if not channel or not isinstance(channel, (discord.DMChannel, discord.TextChannel)):
                return None
        except Exception as ex:
            if not isinstance(ex, discord.errors.NotFound):
                raise MinderBotError(f'General error lookup up channel ID {id}: {ex}', base_exception=ex)

            logger.warning(f'No channel found for ID {id} on guild "{guild.name}" (ID {guild.id}). Not resolving.')
            channel = None

        return channel
