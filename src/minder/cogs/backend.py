import discord
import asyncio
import aiohttp_debugtoolbar
import logging
import jinja2

from aiohttp import web
from aiohttp_jinja2 import setup as setup_jinja
from pprint import pformat
from typing import Optional, Mapping, Any

from minder.config import Config
from minder.cogs.base import BaseCog
from minder.utils import Timezone

logger = logging.getLogger(__name__)


class BackendCog(BaseCog, name='backend'):
    app: web.Application
    runner: web.AppRunner
    site: web.TCPSite
    env: jinja2.Environment

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.app = web.Application(logger=logger, loop=self.bot.loop, debug=Config.ENABLE_DEBUG)
        if Config.ENABLE_DEBUG:
            logger.debug('Loading aiohttp debug toolbar')
            aiohttp_debugtoolbar.setup(self.app)

        self.env = setup_jinja(self.app, loader=jinja2.PackageLoader('minder.web'))
        jinja2.Environment(loader=jinja2.PackageLoader('minder.web'))
        self.app.router.add_get('/', self._get_index, name='index')
        self.app.router.add_get('/members', self._get_members, name='members')
        self.app.router.add_get('/guilds', self._get_guilds, name='guilds')

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

    def _member_to_dict(self, member: discord.Member, use_tz: Optional[Timezone] = None) -> Mapping[str, Any]:
        joined_ts = member.joined_at.timestamp() if not use_tz else member.joined_at.astimezone(use_tz.timezone).ctime()
        return {'id': member.id, 'name': member.name, 'discriminator': member.discriminator, 'joined_ts': joined_ts, 'avatar': str(member.avatar_url)}

    async def _get_index(self, request: web.Request) -> web.Response:
        return web.json_response({'results': [1, 2, 3]})

    async def _get_members(self, request: web.Request) -> web.Response:
        if not self.bot.init_done:
            logger.warning('Received JSONAPI request for guilds before bot was ready..')
            raise web.HTTPInternalServerError(reason='Discord bot is not yet ready')

        mems = {mem.id: {'name': mem.name, 'guild': {mem.guild.id: mem.guild.name}, 'id': mem.id} for mem in self.bot.get_all_members()}

        if not mems:
            logger.warning('No members found querying bot, returning empty response')
            status_code = 204
        else:
            logger.debug(f'Found #{len(mems)} entries:\n{pformat(mems, indent=2)}')
            status_code = 200

        return web.json_response(mems, status=status_code, content_type='application/json')

    async def _get_guilds(self, request: web.Request) -> web.Response:
        use_tz = request.query.get('use_tz', None)

        if not self.bot.init_done:
            logger.warning('Received JSONAPI request for guilds before bot was ready..')
            raise web.HTTPInternalServerError(reason='Discord bot is not yet ready')

        if use_tz:
            if not Timezone.is_valid_timezone(use_tz):
                raise web.HTTPInternalServerError(reason='Invalid timezone name provided: "{use_tz}"')

            use_tz = Timezone.build(use_tz)

        glds = {}

        for gld in self.bot.guilds:
            gld_members = {mem.id: self._member_to_dict(mem, use_tz=use_tz) for mem in gld.members}
            glds[gld.id] = {'id': gld.id, 'name': gld.name, 'description': gld.description, 'owner_id': gld.owner_id, 'members': gld_members}

        if not glds:
            logger.warning('No guild details found, returning empty response')
            status_code = 204
        else:
            logger.debug(f'Found #{len(glds)} entries:\n{pformat(glds, indent=2)}')
            status_code = 200

        return web.json_response(glds, status=status_code, content_type='application/json')
