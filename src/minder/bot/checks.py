import discord
import logging

from discord.ext import commands
from typing import cast

logger = logging.getLogger(__name__)


class MinderCheckFailure(commands.CheckFailure):
    """
    Base check failure class for minder-related checks that do not pass
    """

    def __init__(self, message: str = None) -> None:
        super().__init__(message or 'General bot check failure')


class NoAdminChannel(MinderCheckFailure):
    def __init__(self, message: str = None) -> None:
        message = message or 'No admin channel found'
        super().__init__(message)


def is_admin():
    async def predicate(ctx: commands.Context) -> bool:
        from minder.bot import MinderBot
        bot = cast(MinderBot, ctx.bot)
        usr_cfg = bot.bot_config.get_user(user_id=ctx.author.id)

        if not usr_cfg:
            return False

        return True if usr_cfg.get('is_admin', None) else False

    return commands.check(predicate)


def in_dm():
    async def predicate(ctx: commands.Context) -> bool:
        if not ctx.guild or isinstance(ctx.channel, discord.DMChannel):
            return True

        raise commands.NoPrivateMessage()

    return commands.check(predicate)


def in_admin_channel():
    async def predicate(ctx: commands.Context) -> bool:
        from minder.bot import MinderBot
        bot = cast(MinderBot, ctx.bot)

        if not ctx.guild or isinstance(ctx.channel, discord.DMChannel):
            return False

        guild_cfg = bot.bot_config.get_guild(guild_id=ctx.guild.id)

        if not guild_cfg:
            return False

        bot_chan_id = guild_cfg.get('bot_channel', None)

        if not bot_chan_id:
            return False

        bot_chan = await bot.lookup_channel(by_id=bot_chan_id, context_or_guild=ctx)

        if not bot_chan:
            logger.warning(f'Failed to resolve configured bot admin channel "{bot_chan_id}" to channel reference on "{ctx.guild}"')
            return False

        if bot_chan.id == ctx.channel.id:
            return True

        raise NoAdminChannel()

    return commands.check(predicate)
