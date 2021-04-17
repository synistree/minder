import logging

from datetime import datetime
from discord.ext import commands

from minder.cogs.base import BaseCog

logger = logging.getLogger(__name__)


class StatusCog(BaseCog, name='status'):
    @BaseCog.listener()
    async def on_ready(self, ctx: commands.Context) -> None:
        logger.debug('Bot ready, reporting status every 5 minutes')
        self.bot.scheduler.add_job(self._process_status, trigger='interval', minutes=5)

    async def _process_status(self) -> None:
        dt_now = datetime.now()
        logger.debug(f'Dumping state @ {dt_now.ctime()}')


