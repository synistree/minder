import discord
import logging

from discord.ext import commands
from pprint import pformat

from minder.bot.checks import is_admin
from minder.cogs.base import BaseCog
from minder.settings import SettingsManager
from minder.utils import build_stacktrace_embed

logger = logging.getLogger(__name__)


class SettingsCog(BaseCog):
    manager: SettingsManager

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)

        self.manager = SettingsManager(self.bot.redis_helper)

    @commands.dm_only()
    @commands.group(name='settings')
    async def settings(self, ctx: commands.Context) -> None:
        if not await self.check_ready_or_fail(ctx):
            return

        if ctx.invoked_subcommand:
            return

        settings = self.manager.get_all_settings()
        await ctx.send(content=f'Found #{len(settings)} entries:```\n{settings}\n```')

    @commands.dm_only()
    @settings.command(name='get')
    async def settings_get(self, ctx: commands.Context, name: str) -> None:
        if not await self.check_ready_or_fail(ctx):
            return

        try:
            settings = self.manager.get_setting(name)
            await ctx.send(content=f'Found #{len(settings)} entries:```\n{settings}\n```')
        except Exception as ex:
            logger.warning(f'Unable to fetch requested setting from manager for "{name}": {ex}')
            await ctx.send(content=f'Sorry.. error fetching setting "{name}" from manager: {ex}', embed=build_stacktrace_embed(ex))

    @commands.dm_only()
    @commands.group(name='config')
    async def config(self, ctx: commands.Context) -> None:
        if not await self.check_ready_or_fail(ctx):
            return

    @commands.dm_only()
    @commands.check_any(commands.is_owner(), is_admin())
    @config.command(name='dump')
    async def config_dump(self, ctx: commands.Context) -> None:
        await ctx.send(f'Dumping **ALL** config data:```python\n{pformat(self.bot.bot_config.as_dict(), indent=2)}\n```')

    @commands.dm_only()
    @config.command(name='user')
    async def config_user(self, ctx: commands.Context, for_member: discord.User = None) -> None:
        if for_member:
            user_cfg = self.bot.bot_config.get_user(user_id=for_member.id, throw_error=False)

            if not user_cfg:
                await ctx.send(f'No user config found for "{for_member.name}" (`{for_member.id}`)')
                return

            await ctx.send(f'User config for "{for_member.name}" (`{for_member.id}`):```python\n{pformat(user_cfg)}\n```')
            return

        await ctx.send(f'**ALL** user config:```python\n{pformat(self.bot.bot_config.users, indent=2)}\n```')
