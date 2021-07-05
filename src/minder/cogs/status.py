from __future__ import annotations

import discord
import logging

from discord.ext import commands

from minder.common import DiscordMember, DiscordChannel
from minder.cogs.base import BaseCog
from minder.models.status import StatusEntry

from minder.bot.menus import ConfirmMenu

logger = logging.getLogger(__name__)


class StatusCog(BaseCog, name='status'):
    @BaseCog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        logger.info(f'User joined: {member.name} on {member.guild.name}')
        mem = DiscordMember.from_model(member)
        guild_id, guild_name = member.guild.id, member.guild.name
        join_ctx = {'member': mem, 'guild_name': guild_name, 'guild_id': guild_id}
        ent = StatusEntry.build('JOIN', f'Member "{member.name}" joined "{member.guild.name}"', context=join_ctx)
        ent.store(self.bot.redis_helper)

    @BaseCog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        mem = DiscordMember.from_model(message.author)
        chan = DiscordChannel.from_model(message.channel)

        logger.info(f'Message deleted from "{chan.name}".\n-> Old content: "{message.content}"')
        del_ctx = {'member': mem, 'channel': chan, 'content': message.content}
        ent = StatusEntry.build('DELETE', f'Message deleted from "{chan.name}" by "{mem.name}"', context=del_ctx)
        ent.store(self.bot.redis_helper)

    @BaseCog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        mem = DiscordMember.from_model(after.author)
        chan = DiscordChannel.from_model(after.channel)

        logger.info(f'Message updated in "{chan.name}" by "{mem.name}".\n-> Old content: "{before.content}"\n-> New content: "{after.content}"')
        edit_ctx = {'member': mem, 'channel': chan, 'before': before.content, 'after': after.content}
        ent = StatusEntry.build('EDIT', f'Message edited in "{chan.name}" by "{mem.name}"', context=edit_ctx)
        ent.store(self.bot.redis_helper)

    @commands.command(name='prompt-me')
    async def prompt_me(self, ctx: commands.Context, prompt_with: str) -> None:
        confirm = await ConfirmMenu(f'Are you sure about this {ctx.author.mention}?```\n{prompt_with}\n```').prompt(ctx)

        if not confirm:
            await ctx.send(f'Alrighty, nevermind {ctx.author.mention}')
            return

        await ctx.send(f'10-4 {ctx.author.mention}, would do :wink:')
