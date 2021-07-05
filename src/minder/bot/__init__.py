import discord
import logging
import os.path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from cogwatch import Watcher
from discord.ext import commands
from discord_slash import SlashCommand
from redisent.helpers import RedisentHelper
from sqlalchemy.engine import Engine, create_engine
from typing import Optional, List, Mapping

from minder.config import Config
from minder.cogs.base import BaseCog
from minder.cogs.errors import ErrorHandlerCog
from minder.bot.config import BotConfig
from minder.errors import MinderBotError
from minder.common import MemberType, ChannelType, ContextOrGuildType

logger = logging.getLogger(__name__)
COG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../cogs'))

try:
    import uvloop
except ImportError:
    logger.warning('Cannot find uvloop package, using built in asyncio event loop')
else:
    uvloop.install()
    logger.info('Using uvloop with asyncio')


class MinderBot(commands.Bot):
    redis_helper: RedisentHelper
    sa_engine: Engine
    scheduler: AsyncIOScheduler
    slash_cmd: SlashCommand
    bot_config: BotConfig

    init_done: bool = False

    def __init__(self, **kwargs) -> None:
        kwargs.pop('command_prefix', None)
        if 'description' not in kwargs:
            kwargs['description'] = 'A simple (re)minder bot'

        super().__init__(command_prefix=Config.BOT_PREFIX, intents=discord.Intents.all(), **kwargs)

        self.redis_helper = RedisentHelper(RedisentHelper.build_pool(Config.REDIS_URL))

        do_echo = True if Config.SQLALCHEMY_ECHO else False
        self.sa_engine = create_engine(Config.SQLALCHEMY_URI, echo=do_echo)

        self.scheduler = AsyncIOScheduler({'apscheduler.timezone': Config.USE_TIMEZONE})
        self.scheduler.start()

        if Config.BOT_CONFIG_YAML:
            bot_yaml_path = Config.BOT_CONFIG_YAML
            if not os.path.exists(bot_yaml_path):
                logger.warning(f'Unable to find bot YAML config specified by Config.BOT_CONFIG_YAML in "{bot_yaml_path}". Using empty default')
                self.bot_config = BotConfig()
            else:
                try:
                    self.bot_config = BotConfig.load(Config.BOT_CONFIG_YAML)
                    logger.info(f'Successfully loaded bot YAML config from "{Config.BOT_CONFIG_YAML}" per application config')
                except Exception as ex:
                    logger.error(f'Error loading bot config from "{Config.BOT_CONFIG_YAML}": {ex}. Using empty config.')
                    self.bot_config = BotConfig()

        self.slash_cmd = SlashCommand(self, override_type=True, sync_commands=Config.SYNC_SLASH_COMMANDS)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logger.info('Bot initialization complete.')

        self.watcher = Watcher(self, path='src/minder/cogs', debug=True)
        # Do not actually start watcher, only used for resolving cog names and paths right now
        # await self.watcher.start()

        await self._sync_init()
        self.init_done = True

    async def _sync_init(self) -> None:
        for cog in self.cogs.values():
            await cog._sync_init()

        logger.info('Finished running sync_init on all cogs')

    async def lookup_guild(self, by_id: int = None, by_name: str = None, throw_error: bool = False) -> Optional[discord.Guild]:
        """
        Attempt to lookup a ``discord.Guild`` by "id" or "name"

        This method will attempt to find the desired guild using the provided selector ("id" or "name") using
        the bot-provided ``get_guild`` method.

        :param by_id: the guild ID to fetch
        :param by_name: the guild name to fetch (will attempt to match by name, returning first match)
        :param throw_error: if ``True``, a :py:exc:`MinderBotError` exception will be raised if no guild
                            can be found. Otherwise, ``None`` will be returned.
        """

        if not by_id and not by_name:
            raise MinderBotError('Neither "by_id" nor "by_name" were provided to lookup guild')

        err_message = None
        has_ex = None

        if by_id:
            gld = self.get_guild(by_id)
            if gld:
                return gld

            err_message = f'Unable to find guild by ID "{by_id}" in #{len(self.guilds)} registered guilds'
        else:
            try:
                return discord.utils.get(self.guilds, name=by_name)
            except Exception as ex:
                if isinstance(ex, discord.errors.NotFound):
                    err_message = f'Cannot find guild named "{by_name}" in all #{len(self.guilds)} registered guilds'
                else:
                    err_message = f'General error attempting to lookup guild "{by_name}": {ex}'

                has_ex = ex

            if err_message:
                gld_out = '\n -> '.join([f'{gld.name} ({gld.id})' for gld in self.guilds])
                logger.warning(err_message)
                logger.debug(f'All guilds:\n{gld_out}')

                if throw_error:
                    raise MinderBotError(err_message, base_exception=has_ex) from has_ex

        return None

    async def lookup_channel(self, by_id: int = None, by_name: str = None, context_or_guild: ContextOrGuildType = None,
                             throw_error: bool = False) -> Optional[ChannelType]:
        """
        Attempt to lookup a ``discord.TextChannel`` by "id" or "name"

        This method will attempt to lookup a channel using the provided selector and, if not found will raise a
        :py:exc:`MinderBotError` or return ``None`` based on the provided ``throw_error`` value.

        :param by_id: lookup based by ID using provided integer
        :param by_name: lookup based on the provided username
        :param context_or_guild: either the provided ``commands.Context`` or ``discord.Guild`` instance will be used
                                 to lookup the channel. if using a discord Context, the ``context.guild`` value will
                                 be used.
        :param context: optional ``discord.ext.commands.Context`` instance (if available). this can be used in place
                        of a guild, if not otherwise provided and should be passed whenever available
        :param throw_error: if ``True``, a :py:exc:`MinderBotError` exception will be raised if no channel
                            can be found. Otherwise, ``None`` will be returned.
        """

        if not by_id and not by_name:
            raise MinderBotError('Neither "by_id" nor "by_name" provided to lookup channel')

        if context_or_guild:
            guild = context_or_guild.guild if isinstance(context_or_guild, commands.Context) else context_or_guild
        else:
            guild = None

        err_message = None
        has_ex = None

        if by_id:
            try:
                chan = await self.fetch_channel(by_id)

                if not isinstance(chan, (discord.TextChannel, discord.DMChannel,)):
                    return None

                return chan
            except Exception as ex:
                has_ex = ex
                if isinstance(ex, discord.errors.NotFound) and guild:
                    logger.info(f'Bot cannot find channel with ID "{by_id}". Attmempting to use provided "{guild.name}" guild')

                    # Will return "None" if the channel is not found anyway
                    chan = guild.get_channel(by_id)  # type: ignore[assignment]

                    if chan:
                        return chan  # type: ignore[return-value]

                    err_message = f'No channel with ID "{by_id}" found using bot lookup'
                else:
                    err_message = f'General error attempting to lookup channel with ID "{by_id}": {ex}'

                if throw_error:
                    ctx = context_or_guild if isinstance(context_or_guild, commands.Context) else None
                    raise MinderBotError(err_message, base_exception=ex, context=ctx) from ex

                logger.error(err_message)

            return None

        try:
            chan = discord.utils.get(guild.channels if guild else self.get_all_channels(), name=by_name)  # type: ignore[assignment]

            if not isinstance(chan, (discord.DMChannel, discord.TextChannel,)):
                return None

            if chan:
                return chan  # type: ignore[return-value]
        except Exception as ex:
            err_message = f'Error looking up channels: {ex}'
            has_ex = ex

        if not err_message:
            err_message = f'Unexpected error while attempting to lookup channel "{by_name}"'

        if throw_error:
            ctx = context_or_guild if isinstance(context_or_guild, commands.Context) else None
            raise MinderBotError(err_message, base_exception=has_ex, context=ctx) from has_ex

        logger.error(err_message)
        return None

    async def lookup_member(self, by_id: int = None, by_name: str = None, context_or_guild: ContextOrGuildType = None,
                            throw_error: bool = False) -> Optional[MemberType]:
        """
        Attempt to lookup a ``discord.Member`` by "id" ir "name"

        This method will attempt to lookup a member using the provided selector and, if not found will raise
        a :py:exc:`MinderBotError` or return ``None`` based on the provided ``throw_error`` value

        :param by_id: lookup based by ID using provided integer
        :param by_name: lookup based on the provided username
        :param guild: if provided, lookup member using the provided :py:class:`GuildType` which can
                      be a integer (interpreted as a Guild ID) or a ``discord.Guild`` instance
        :param context_or_guild: either the provided ``commands.Context`` or ``discord.Guild`` instance will be used
                                 to lookup the channel. if using a discord Context, the ``context.guild`` value will
                                 be used.
        :param throw_error: if ``True``, a :py:exc:`MinderBotError` exception will be raised if no member
                            can be found. Otherwise, ``None`` will be returned.
        """

        if not by_id and not by_name:
            raise MinderBotError('Neither "by_id" nor "by_name" provided to lookup channel')

        if not context_or_guild:
            # TODO: Add lookup by bot here
            return None

        # TODO: Also fix this case
        if not by_id:
            return None

        guild = context_or_guild.guild if isinstance(context_or_guild, commands.Context) else context_or_guild

        if not guild:
            return None

        return await guild.fetch_member(by_id)

    def get_all_cogs(self, use_dotted_path: bool = True) -> Mapping[str, commands.Cog]:
        if not use_dotted_path:
            return dict(self.cogs)

        return {f'minder.cogs.{c_name}': c_ent for c_name, c_ent in self.cogs.items()}

    def get_cog_path(self, name: str, use_dotted_path: bool = False, throw_error: bool = True) -> Optional[str]:
        if name not in self.cogs:
            err_message = f'No such cog found "{name}"'

            if throw_error:
                raise MinderBotError(err_message)

            logger.info(err_message)
            return None

        cog_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f'../minder/cogs/{name}.py'))

        if not os.path.exists(cog_path):
            err_message = f'Cannot find cog file in "minder/cogs/{name}.py"'

            if throw_error:
                raise MinderBotError(err_message)

        return f'minder.cogs.{name}' if use_dotted_path else f'minder/cogs/{name}.py'

    async def reload_cogs(self, cog_name: str = None) -> List[str]:
        if cog_name:
            if cog_name not in self.cogs:
                raise MinderBotError(f'Failure reloading cog "{cog_name}": Not found')

            cogs = [cog_name]
        else:
            cogs = list(self.cogs.keys())

        logger.info(f'Reloading cogs based on request from user. Cogs: "{cogs}"')

        reloaded_cogs = []

        for cog in cogs:
            if cog == 'base':
                continue

            if not os.path.exists(os.path.join(COG_PATH, f'{cog}.py')):
                logger.warning(f'Cannot find cog path for "{cog}". Skipping..')
                continue

            cog_dot_path = f'minder.cogs.{cog}.py'
            cog_path = self.watcher.get_cog_name(cog_dot_path)
            logger.debug(f'-> Reloading "{cog_path}" ("{cog_dot_path}")')
            await self.watcher.reload(cog_path)
            reloaded_cogs.append(cog)

        logger.info(f'Successfully re-registered cogs: "{", ".join(reloaded_cogs)}"')
        return reloaded_cogs


def build_bot(use_token: str = None, start_bot: bool = True, **bot_kwargs) -> MinderBot:
    use_token = use_token or Config.BOT_TOKEN
    bot = MinderBot(**bot_kwargs)
    bot.add_cog(BaseCog(bot))
    bot.add_cog(ErrorHandlerCog(bot))

    for cog_cls in BaseCog._subclasses:
        logger.info(f'Registering cog "{cog_cls.cog_name}"')
        bot.add_cog(cog_cls(bot))

    if not start_bot:
        return bot

    logger.info('Starting bot..')
    bot.run(use_token)
