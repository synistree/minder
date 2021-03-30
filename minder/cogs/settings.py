import logging

from discord.ext import commands

from minder.cogs.base import BaseCog

logger = logging.getLogger(__name__)


class SettingsCog(BaseCog):
    @commands.guild_only()
    @commands.group(name='settings')
    async def settings(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand:
            return

        if not self.bot_ready or not self.bot.init_done:
            await ctx.send(f'Sorry {ctx.author.mention}, bot is not done loading yet..')
            return

        await ctx.send('User settings:\n...')
