from __future__ import annotations

import logging

from discord_slash import cog_ext, SlashContext, utils

from minder.cogs.base import BaseCog
from minder.config import Config

logger = logging.getLogger(__name__)


class SlashCog(BaseCog, name='slash'):
    @cog_ext.cog_slash(name='mrow')
    async def _mrow(self, ctx: SlashContext):
        # embed = discord.Embed(title='MROW', description=f':cat: {ctx.author.mention} :smile:')
        # await ctx.send(content=f'mrow back at you {ctx.author.name}', embeds=[embed])
        cmds = await utils.manage_commands.get_all_commands(self.bot.client.id, bot_token=Config.BOT_TOKEN)
        logger.info(f'Commands:\n{cmds}')
        await ctx.send(content=f'Commands:\n```\n{cmds}\n```')

    @cog_ext.cog_slash(name='sync-slash-commands')
    async def _sync_slash_commands(self, ctx: SlashContext) -> None:
        logger.info(f'Triggering sync of slash commands based on request from "{ctx.author.name}"')
        await self.bot.slash_cmd.sync_all_commands()
        await ctx.send(content='Trigger sync of all slash commands')
