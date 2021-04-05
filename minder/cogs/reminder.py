import discord
import logging
import humanize

from datetime import datetime
from discord.ext import commands
from typing import List

from minder.cogs.base import BaseCog
from minder.config import Config
from minder.models import Reminder
from minder.utils import FuzzyTimeConverter

logger = logging.getLogger(__name__)


class ReminderCog(BaseCog):
    async def _sync_init(self) -> None:
        self.bot.scheduler.add_job(self._process_reminders, trigger='interval', seconds=int(Config.DEFAULT_CHECK_INTERVAL))

        # Call immediately.
        await self._process_reminders()

        logger.info('Reminder cog scheduled job registered. Starting scheduler..')
        self.bot.scheduler.start()

    async def _process_reminders(self) -> None:
        logger.info('In scheduled reminder check.')

        reminders = self._get_reminders()

        if not reminders:
            return

        for rem in reminders:
            if rem.is_complete:
                continue

            dt_now = datetime.now()
            t_delta = dt_now - rem.trigger_dt
            t_offset = 14400  # 4 hours
            # 10 * int(Config.DEFAULT_CHECK_INTERVAL)
            if t_delta.total_seconds() > t_offset:
                nice_total = humanize.naturaltime(t_delta.total_seconds(), future=False)
                logger.info(f'Found reminder that has been elapsed for {nice_total} with t_offset set {t_offset}. Skipping.')
                continue

            author, channel = None, None

            channel = await self.bot.fetch_channel(rem.channel_id) if rem.channel_id else None

            author = await self.bot.fetch_user(rem.member_id)

            if not channel:
                logger.info(f'Reminder has no associated channel, DMing "{author.name}" instead')

            msg_target = channel if channel else author
            msg_out = f':wave: {author.mention if channel else author.name}, here is your reminder:\n{rem.as_markdown(author, channel=channel)}'
            logger.info(f'Triggered reminder response for "{msg_target}":\n{rem.dump()}')
            
            try:
                await msg_target.send(msg_out)
            except Exception as ex:
                logger.error(f'Error sending reminder to "{msg_target}": {ex}')
                logger.debug(f'Dumped reminder:\n{rem.dump()}')
                continue
            else:
                rem.is_complete = True
                rem.store(self.bot.redis_helper)
                logger.info(f'Successfully marked reminder for "{rem.member_name}" complete')

        logger.info('Finished scheduled reminder check.')

    def _get_reminders(self, member_id: int = None, include_complete: bool = True) -> List[Reminder]:
        rem_keys = self.bot.redis_helper.keys(redis_id='reminders')
        if not rem_keys:
            return []

        reminders = []

        for rem_id in rem_keys:
            rem = Reminder.fetch(self.bot.redis_helper, redis_id='reminders', redis_name=rem_id)

            if not rem:
                logger.warning(f'Unexpectedly missing reminder for "{rem_id}"')
                continue

            if not include_complete and rem.is_complete:
                logger.info(f'Skipping reminder for "{rem_id}" since reminder is marked complete')
                continue

            reminders.append(rem)

        return reminders

    @commands.guild_only()
    @commands.group(name='reminders')
    async def reminders(self, ctx: commands.Context) -> None:
        if not self.bot.init_done:
            await ctx.send(f'Sorry {ctx.author.mention}, bot is not done loading yet..')
            return
        
        if ctx.invoked_subcommand:
            return

        reminders = self._get_reminders(include_complete=False)

        msg_out = f'Hey {ctx.author.mention}, found #{len(reminders)} pending reminders:'
        for rem in reminders:
            msg_out += f'\n{rem.as_markdown(ctx.author, ctx.channel)}'

        await ctx.send(msg_out)

    @commands.guild_only()
    @reminders.command(name='all')
    async def all_reminders(self, ctx: commands.Context) -> None:
        reminders = self._get_reminders(include_complete=True)

        msg_out = f'Hey {ctx.author.mention}, found #{len(reminders)} reminders (**ALL** reminders):'
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
