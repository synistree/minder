import discord
import logging
import traceback

from discord.ext import commands

from redisent.errors import RedisError

logger = logging.getLogger(__name__)


class ErrorHandlerCog(commands.Cog):
    IGNORED_EXCEPTIONS = (commands.CommandNotFound,)

    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """
        Cog-registered error handler for :py:exc:`commands.CommandError` exceptions

        This handler will first attempt to output sane, helpful log entries and then make the final
        determination on how error reporting to the caller of the command shall proceed.

        :param ctx: the context from the command invocation
        :param error: the raised :py:cls:`commands.Context` exception to process
        """

        if hasattr(ctx.command, 'on_error'):
            # Let the existing on_error handler deal with this.
            return

        cog = ctx.cog

        if cog and cog._get_overridden_method(cog.cog_command_error) is not None:
            # Let the existing cog-related on_command_error handler deal with this.
            return

        error = getattr(error, 'original', error)
        if isinstance(error, self.IGNORED_EXCEPTIONS):
            # Don't bother processing further if there exception is of a type in IGNORED_EXCEPTIONS
            return

        logger.error(f'[default on_command_error:{ctx.command}] Unhandled error from "{ctx.command}": {error}')

        if hasattr(error, '__traceback__'):
            exc_info = traceback.format_exception(type(error), error, error.__traceback__)
        else:
            exc_info = traceback.format_exc(chain=True)

        logger.info(f'Traceback:\n{"".join(exc_info)}')

        if isinstance(error, commands.DisabledCommand):
            await ctx.send(f'Sorry {ctx.author.mention} but `{ctx.command}` has been disabled.')
        elif isinstance(error, commands.NoPrivateMessage):
            logger.error(f'Received guild-only command {ctx.command} from {ctx.author.name}')
            try:
                await ctx.author.send(f'Eek.. `{ctx.command}` can not be used in Private Messages.')
            except discord.HTTPException:
                pass
        elif isinstance(error, commands.errors.PrivateMessageOnly):
            logger.error(f'Received dm-only command for {ctx.command} in {ctx.channel.name} from {ctx.author.name}')
            await ctx.send(f'Sorry {ctx.author.mention}, {ctx.command} can only be used in DMs')
        elif isinstance(error, commands.BadArgument):
            if ctx.command.qualified_name == 'tag list':
                await ctx.send(f'Sorry {ctx.author.mention}, bad argument value for `{ctx.command}`: {error}')

            logger.warning(f'Bad argument provided for "{ctx.command}": {error}')
        elif isinstance(error, RedisError):
            logger.error(f'Redis error encountered in "{ctx.command}": {error}')
            if error.is_connection_error:
                await ctx.send(f'Sorry {ctx.author.mention}, unable to connect to the backend')
        else:
            logger.warning(f'[default on_command_error:{ctx.command}] Silently ignoring error {error} and not reporting')
