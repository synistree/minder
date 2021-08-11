import asyncio
import aiohttp_debugtoolbar
import logging
import jinja2

from aiohttp import web
from aiohttp_jinja2 import setup as setup_jinja
from discord.ext import tasks

from minder.config import Config
from minder.cogs.base import BaseCog

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()


class BackendCog(BaseCog, name='backend'):
    app: web.Application = None
    runner: web.AppRunner = None
    site: web.TCPSite = None
    env: jinja2.Environment = None

    _web_running: bool = None

    @property
    def bot_url(self) -> str:
        proto = 'https' if Config.SSL_ENABLE else 'http'

        if self.runner and self.runner.addresses:
            (host, port) = self.runner.addresses[0]
            return f'{proto}://{host}:{port}'

        return f'{proto}://{Config.BOT_WEB_HOST}:{Config.BOT_WEB_PORT}'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.app = web.Application(logger=logger, debug=Config.ENABLE_DEBUG)
        if Config.ENABLE_DEBUG:
            logger.debug('Loading aiohttp debug toolbar')
            aiohttp_debugtoolbar.setup(self.app)

        self.app['bot'] = self.bot
        self.env = setup_jinja(self.app, loader=jinja2.PackageLoader('minder.web'))

        # Import views to populate routes table and register
        import minder.bot.views  # noqa: F401
        self.app.add_routes(routes)

        self.runner = web.AppRunner(self.app, handle_signals=True)

    async def _sync_init(self) -> None:
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, host=Config.BOT_WEB_HOST, port=int(Config.BOT_WEB_PORT))
        logger.info('Starting up cog backend web server..')
        await self.site.start()

    @tasks.loop()
    async def _run_webserver(self) -> None:
        self._web_running = True
        logger.info(f'Bot backend up at http://{Config.BOT_WEB_HOST}:{Config.BOT_WEB_PORT}')

    @_run_webserver.before_loop
    async def _before_start_webserver(self) -> None:
        logger.info('Waiting for bot finish loading before starting aiohttp web server cog')
        await self.bot.wait_until_ready()
        logger.info('Bot ready. Starting aiohttp webserver')

    def __unload(self) -> None:
        if not self._web_running or not self.site:
            logger.debug(f'Found no running aiohttp backend cog server running. (_web_running: {self._web_running}, site: {self.site})')
            return

        logger.info('Backend cog unloading, stopping web backend..')
        asyncio.ensure_future(self.site.stop())
