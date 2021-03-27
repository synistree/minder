import logging

from discord.ext import commands
from redisent.helpers import RedisentHelper

from minder.config import Config
from minder.cogs import all_cogs

logger = logging.getLogger(__name__)


class MinderBot(commands.Bot):
    init_done: bool = False

    def __init__(self, **kwargs) -> None:
        kwargs.pop('command_prefix', None)
        if 'description' not in kwargs:
            kwargs['description'] = 'A simple (re)minder bot'

        super().__init__(command_prefix=Config.BOT_PREFIX, **kwargs)

        self.redis_helper = RedisentHelper(RedisentHelper.build_pool(Config.REDIS_URL))

        self._sync_init()
        self.init_done = True

    def _sync_init(self) -> None:
        for cog in self.cogs.values():
            init_fn = getattr(cog, '_sync_init', None)
            if init_fn:
                init_fn()

        logger.info('Finished running sync_init on all cogs')


def build_bot(use_token: str = None, start_bot: bool = True, **bot_kwargs) -> MinderBot:
    bot = MinderBot(**bot_kwargs)

    for cog_cls in all_cogs:
        logger.info(f'Registering cog "{cog_cls.__name__}"')
        bot.add_cog(cog_cls(bot))

    if start_bot:
        bot.run(use_token or Config.BOT_TOKEN)

    return bot
