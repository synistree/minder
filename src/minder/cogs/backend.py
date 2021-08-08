import asyncio
import aiohttp_debugtoolbar
import logging
import jinja2

from aiohttp import web
from aiohttp_jinja2 import setup as setup_jinja

from minder.config import Config
from minder.cogs.base import BaseCog

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()


class BackendCog(BaseCog, name='backend'):
    app: web.Application
    runner: web.AppRunner
    site: web.TCPSite
    env: jinja2.Environment

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.app = web.Application(logger=logger, debug=Config.ENABLE_DEBUG)
        if Config.ENABLE_DEBUG:
            logger.debug('Loading aiohttp debug toolbar')
            aiohttp_debugtoolbar.setup(self.app)

        self.app['bot'] = self.bot
        self.env = setup_jinja(self.app, loader=jinja2.PackageLoader('minder.bot'))
        jinja2.Environment(loader=jinja2.PackageLoader('minder.bot'))

        # Import views to populate routes table and register
        import minder.bot.views  # noqa: F401
        self.app.add_routes(routes)

        self.runner = web.AppRunner(self.app)

    async def _sync_init(self) -> None:
        logger.info('Starting up cog backend web server..')
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, host=Config.BOT_WEB_HOST, port=int(Config.BOT_WEB_PORT))
        await self.site.start()
        logger.info(f'Bot backend up at http://{Config.BOT_WEB_HOST}:{Config.BOT_WEB_PORT}')

    def __unload(self) -> None:
        logger.info('Backend cog unloading, stopping web backend..')
        asyncio.ensure_future(self.site.stop())
