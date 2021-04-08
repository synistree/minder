import logging

from discord.ext import commands

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
        if ctx.invoked_subcommand:
            return

        if not self.bot.init_done:
            await ctx.send(f'Sorry {ctx.author.mention}, bot is not done loading yet..')
            return

        settings = self.manager.get_all_settings()
        await ctx.send(content=f'Found #{len(settings)} entries:```\n{settings}\n```')

    @commands.dm_only()
    @settings.command(name='get')
    async def settings_get(self, ctx: commands.Context, name: str) -> None:
        if not self.bot.init_done:
            await ctx.send(f'Sorry {ctx.author.mention}, bot is not done loading yet..')
            return

        try:
            settings = self.manager.get_setting(name)
            await ctx.send(content=f'Found #{len(settings)} entries:```\n{settings}\n```')
        except Exception as ex:
            logger.warning(f'Unable to fetch requested setting from manager for "{name}": {ex}')
            await ctx.send(content=f'Sorry.. error fetching setting "{name}" from manager: {ex}', embed=build_stacktrace_embed(ex))
