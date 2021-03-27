import logging
import discord

from discord.ext import commands
from typing import List

from minder.models import Reminder
from minder.utils import FuzzyTimeConverter

logger = logging.getLogger(__name__)


class ReminderCog(commands.Cog):
    bot: commands.Bot

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    def _get_reminders(self, member_id: int = None) -> List[Reminder]:
        rem_keys = self.bot.redis_helper.keys(redis_id='reminders')
        if not rem_keys:
            return []

        reminders = []
        
        for rem_id in rem_keys:
            rem = Reminder.fetch(self.bot.redis_helper, redis_id='reminders', redis_name=rem_id)

            if not rem:
                logger.warning(f'Unexpectedly missing reminder for "{rem_id}"')
            else:
                reminders.append(rem)

        return reminders

    @commands.guild_only()
    @commands.group(name='reminders')
    async def reminders(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand:
            return

        if not self.bot.init_done:
            await ctx.send(f'Sorry {ctx.author.mention}, bot is not done loading yet..')
            return

        reminders = self._get_reminders()

        msg_out = f'Hey {ctx.author.mention}, found #{len(reminders)} reminders:'
        for rem in reminders:
            msg_out += f'\n{rem.as_markdown(ctx.author, ctx.channel)}'

        await ctx.send(msg_out)

    @commands.guild_only()
    @reminders.command(name='add')
    async def add_reminder(self, ctx: commands.Context, fuzzy_when: FuzzyTimeConverter, *, content: str) -> None:
        reminder = Reminder.build(fuzzy_when, ctx.author, ctx.channel, content)

        reminder.store(self.bot.redis_helper)
        reminder_md = reminder.as_markdown(ctx.author, ctx.channel, as_embed=True)
        logger.info(f'Successfully added new reminder for "{ctx.author.name}"')
        logger.debug(f'Reminder:\n{reminder.dump()}')

        await ctx.send(f'Adding new reminder for {ctx.author.mention}', embed=reminder_md)

    @commands.guild_only()
    @reminders.command(name='clean')
    async def clean_reminders(self, ctx: commands.Context, for_member: discord.Member = None) -> None:
        reminders = self._get_reminders(member_id=for_member.id if for_member else None)

        if not reminders:
            await ctx.send(f'Sorry {ctx.author.mention} but no reminders found in database')
            return

        msg_out = f'Found #{len(reminders)} reminders to check'

        if for_member:
            msg_out += f' for "{for_member.name}" (ID: "{for_member.id}")'

        logger.info(f'{msg_out}. Requested in "{ctx.channel.name}" by "#{ctx.author.name}" on "{ctx.guild.name}"')
        cnt = 0

        for rem in reminders:
            try:
                if not rem.is_complete:
                    continue

                logger.debug(f'Running hdel() on "{rem.redis_name}" for "{rem.member_name}"')
                with self.bot.redis_helper.wrapped_redis(f'hdel("reminders", "{rem.redis_name}")') as r_conn:
                    r_conn.hdel('reminders', rem.redis_name)

                cnt += 1
            except Exception as ex:
                await ctx.send(f'Sorry {ctx.author.mention} but encountered an error attempting to delete reminders')
                logger.exception(f'Failure while attempting to delete reminders from Redis: {ex}')
                continue

        await ctx.send(f'{msg_out}... Removed #{cnt}. :smile:')

    @commands.guild_only()
    @reminders.command(name='lookup')
    async def lookup_reminder(self, ctx: commands.Context, target_member: discord.Member = None) -> None:
        pass
