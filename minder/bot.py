import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.ext import commands
from redisent.helpers import RedisentHelper
from sqlalchemy.engine import Engine, create_engine

from minder.config import Config
from minder.cogs.base import BaseCog

logger = logging.getLogger(__name__)


class MinderBot(commands.Bot):
    redis_helper: RedisentHelper
    sa_engine: Engine
    scheduler: AsyncIOScheduler

    is_ready: bool = False
    init_done: bool = False

    def __init__(self, **kwargs) -> None:
        kwargs.pop('command_prefix', None)
        if 'description' not in kwargs:
            kwargs['description'] = 'A simple (re)minder bot'

        super().__init__(command_prefix=Config.BOT_PREFIX, **kwargs)

        self.redis_helper = RedisentHelper(RedisentHelper.build_pool(Config.REDIS_URL))

        do_echo = True if Config.SQLALCHEMY_ECHO else False
        self.sa_engine = create_engine(Config.SQLALCHEMY_URI, echo=do_echo)

        from minder.db import Base
        Base.metadata.create_all(self.sa_engine)

        self.scheduler = AsyncIOScheduler({'apscheduler.timezone': Config.USE_TIMEZONE})

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.is_ready = True
        logger.info('Bot initialization complete.')

        await self._sync_init()
        self.init_done = True

    async def _sync_init(self) -> None:
        for cog in self.cogs.values():
            init_fn = getattr(cog, '_sync_init', None)
            if init_fn:
                await init_fn()

        logger.info('Finished running sync_init on all cogs')


def build_bot(use_token: str = None, start_bot: bool = True, **bot_kwargs) -> MinderBot:
    bot = MinderBot(**bot_kwargs)
    bot.add_cog(BaseCog(bot))

    for cog_cls in BaseCog._subclasses:
        logger.info(f'Registering cog "{cog_cls.__name__}"')
        bot.add_cog(cog_cls(bot))

    if start_bot:
        bot.run(use_token or Config.BOT_TOKEN)

    return bot
