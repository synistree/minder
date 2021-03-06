from __future__ import annotations

import discord
import logging
import humanize

import discord.ext.menus as menus  # type: ignore

from datetime import datetime
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from typing import List, Optional, cast

from minder.bot.checks import is_admin
from minder.bot.menus import ConfirmMenu
from minder.cogs.base import BaseCog
from minder.common import ChannelType
from minder.errors import build_stacktrace_embed
from minder.models import Reminder
from minder.utils import FuzzyTimeConverter, Timezone, FuzzyTime, EMOJIS

logger = logging.getLogger(__name__)


class ReminderMenu(menus.Menu):
    reminder: Reminder
    header: str

    result: Optional[bool] = None

    KEEP_EMOJI = EMOJIS[':white_check_mark:']
    REMOVE_EMOJI = EMOJIS[':heavy_multiplication_x:']

    def __init__(self, reminder: Reminder, *args, header: str = None, timeout: float = None, **kwargs) -> None:
        kwargs['timeout'] = timeout or 30.0
        kwargs['clear_reactions_after'] = True
        super().__init__(*args, **kwargs)

        self.reminder = reminder
        self.header = header or 'Keep or purge this reminder?'

    async def send_initial_message(self, ctx: commands.Context, channel: ChannelType) -> discord.Message:
        rem_md = cast(discord.Embed, self.reminder.as_markdown(author=ctx.author, channel=channel, as_embed=True))
        return await channel.send(self.header, embed=rem_md)

    @menus.button(KEEP_EMOJI)
    async def on_keep(self, payload) -> None:
        logger.info(f'Received keep confirmation on {payload}')
        self.result = True

        await self.message.edit(content=f'Thanks {self.ctx.author.mention}, will keep this reminder.', delete_after=self.timeout)

        self.stop()

    @menus.button(REMOVE_EMOJI)
    async def on_remove(self, payload) -> None:
        logger.info(f'Received removal confirmation on {payload}')
        self.result = False

        await self.message.edit(content=f'Sounds good {self.ctx.author.mention}, removing this reminder.', delete_after=self.timeout)

        self.stop()

    async def prompt(self, ctx: commands.Context, channel: discord.abc.Messageable = None) -> bool:
        await self.start(ctx, channel=channel, wait=True)
        return True if self.result else False


class ReminderCog(BaseCog, name='reminder'):
    async def _sync_init(self) -> None:
        logger.info('Starting scheduler in Reminder cog and processing and pending Reminders')

        await self._process_reminders()

    async def _process_reminders(self) -> None:
        reminders = self._get_reminders(include_complete=False)

        if not reminders:
            return

        dt_now = datetime.now()

        logger.info(f'Found #{len(reminders)} pending reminders to schedule..')

        for rem in reminders:
            num_seconds_left = rem.trigger_time.num_seconds_left

            if not num_seconds_left:
                logger.warning(f'Found reminder that appeared to be pending with num_seconds_left not set for "{rem.redis_name}". Skipping..')
                continue

            nice_seconds = humanize.naturaltime(num_seconds_left, future=True)
            logger.info(f'Scheduling reminder job for "{rem.redis_name}" in {num_seconds_left} seconds ({nice_seconds})')
            self.bot.scheduler.add_job(self._process_reminder, kwargs={'reminder': rem, 'added_at': dt_now}, trigger='date', run_date=rem.trigger_dt,
                                       id=rem.redis_name)

    async def _process_reminder(self, reminder: Reminder, added_at: datetime = None) -> bool:
        added_at = added_at or datetime.now()
        author, channel = None, None

        channel = await self.bot.fetch_channel(reminder.channel_id) if reminder.channel_id else None
        author = await self.bot.fetch_user(reminder.member_id)

        if not channel:
            logger.info(f'Reminder has no associated channel, DMing "{author.name}" instead')

        msg_target = channel if channel else author
        msg_out = f':wave: {author.mention if channel else author.name}, here is your reminder:\n{reminder.as_markdown(author, channel=channel)}'
        logger.info(f'Triggered reminder response for "{msg_target}":\n{reminder.dump()}')

        try:
            await msg_target.send(msg_out)
        except Exception as ex:
            logger.error(f'Error sending reminder to "{msg_target}": {ex}')
            logger.debug(f'Dumped reminder:\n{reminder.dump()}')
            return False
        else:
            reminder.user_notified = True
            reminder.store(self.bot.redis_helper)
            logger.info(f'Successfully marked reminder for "{reminder.member_name}" complete')

        logger.info('Finished scheduled reminder check.')
        return True

    def _get_reminders(self, member_id: int = None, include_complete: bool = True) -> List[Reminder]:
        rem_keys = self.bot.redis_helper.keys(redis_id='reminders')
        if not rem_keys:
            return []

        reminders: List[Reminder] = []

        for rem_id in rem_keys:
            rem = cast(Reminder, Reminder.fetch(self.bot.redis_helper, redis_id='reminders', redis_name=rem_id))

            if not rem:
                logger.warning(f'Unexpectedly missing reminder for "{rem_id}"')
                continue

            if not include_complete and rem.is_complete:  # type: ignore[attr-defined]
                logger.info(f'Skipping reminder for "{rem_id}" since reminder is marked complete')
                continue

            reminders.append(rem)

        return reminders

    @cog_ext.cog_subcommand(base='reminders', name='list', description='List all or pending reminders')
    async def _reminders_list(self, ctx: SlashContext, include_complete: bool = False) -> None:
        if not self.bot.init_done:
            await ctx.send('Sorry, the bot is not yet loaded.. Try again in a few moments')
            return

        reminders = self._get_reminders(include_complete=include_complete)
        all_rem = '**ALL** reminders' if not include_complete else 'pending reminders'
        msg_out = f'Found #{len(reminders)} {all_rem}:'
        for rem in reminders:
            msg_out += f'\n{rem.as_markdown(ctx.author, ctx.channel)}'

        await ctx.send(msg_out)

    @cog_ext.cog_subcommand(base='reminders', name='add', description='Add a new reminder')
    async def _reminders_add(self, ctx: SlashContext, when: str, content: str, timezone: str = None) -> None:
        if not self.bot.init_done:
            await ctx.send('Sorry, the bot is not yet loaded.. Try again in a few moments')
            return

        if not timezone:
            timezone = self.bot.bot_config.get_user_setting(ctx.author.id, 'timezone', default=None) or 'UTC'

        if not Timezone.is_valid_timezone(timezone):
            await ctx.send(f'Invalid timezone provided "{timezone}".. :slight_frown:')
            return

        user_tz = Timezone.build(timezone)

        fuzzy_when = FuzzyTime.build(provided_when=when, use_timezone=user_tz)
        reminder = Reminder.build(fuzzy_when, member=ctx.author, channel=ctx.channel, content=content)  # type: ignore[arg-type]

        reminder.store(self.bot.redis_helper)
        reminder_md = cast(discord.Embed, reminder.as_markdown(ctx.author, as_embed=True))  # type: ignore[arg-type]
        logger.info(f'Successfully created a new reminder for "{ctx.author.name}" via slash command')
        logger.debug(f'Slash Command Reminder Reminder:\n{reminder.dump()}')

        self.bot.scheduler.add_job(self._process_reminder, kwargs={'reminder': reminder, 'added_at': datetime.now()}, trigger='date',
                                   run_date=reminder.trigger_dt, id=reminder.redis_name)
        logger.info(f'Scheduled new reminder job at "{reminder.trigger_dt.ctime()}"')

        await ctx.send(f'Adding new reminder for `{fuzzy_when.resolved_time.ctime()}` :wink:', embed=reminder_md)

    @cog_ext.cog_subcommand(base='reminders', name='clean', description='Purge completed or all reminders')
    async def _reminders_clean(self, ctx: SlashContext, complete_only: bool = True, member: discord.Member = None):
        action = 'ALL' if not complete_only else 'pending'
        await ctx.send(f'Would purge `{action}` reminders. member: {member}')

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx: SlashContext, ex: Exception) -> None:
        logger.error(f'Error running slash command for "{ctx.command}" for "{ctx.author.name}": {ex}')
        await ctx.send(f'Error running "{ctx.command}": {ex} :frowning:', embeds=[build_stacktrace_embed(ex)])

    @commands.guild_only()
    @commands.group(name='reminders')
    async def reminders(self, ctx: commands.Context) -> None:
        if not self.bot.init_done:
            await ctx.send(f'Sorry {ctx.author.mention}, bot is not done loading yet..')
            return

        if ctx.invoked_subcommand:
            return

        reminders = self._get_reminders(include_complete=False)

        author_name = ctx.author.mention if isinstance(ctx.channel, discord.channel.TextChannel) else ctx.author.name

        msg_out = f'Hey {author_name}, found #{len(reminders)} pending reminders:'
        for rem in reminders:
            msg_out += f'\n{rem.as_markdown(ctx.author, ctx.channel)}'  # type: ignore[arg-type]

        await ctx.send(msg_out)

    @commands.guild_only()
    @reminders.command(name='all')
    async def all_reminders(self, ctx: commands.Context) -> None:
        reminders = self._get_reminders(include_complete=True)

        msg_out = f'Hey {ctx.author.mention}, found #{len(reminders)} reminders (**ALL** reminders):'
        for rem in reminders:
            msg_out += f'\n{rem.as_markdown(ctx.author, ctx.channel)}'  # type: ignore[arg-type]

        await ctx.send(msg_out)

    @commands.check_any(commands.is_owner(), is_admin())
    @commands.guild_only()
    @reminders.command(name='review')
    async def review_reminders(self, ctx: commands.Context, member: discord.Member = None) -> None:
        reminders = self._get_reminders(include_complete=False)

        if member:
            reminders = [rem for rem in reminders if rem.member_id == member.id]

        for rem in reminders:
            menu = ReminderMenu(rem)
            res = await menu.prompt(ctx)
            logger.info(f'Reminder review response: {res}')

        # pages = menus.MenuPages(source=ReminderMenuSource(reminders))
        # await pages.start(ctx)

    @commands.guild_only()
    @reminders.command(name='add')
    async def add_reminder(self, ctx: commands.Context, fuzzy_when: FuzzyTimeConverter, *, content: str) -> None:
        dt_now = datetime.now()
        reminder = Reminder.build(fuzzy_when, member=ctx.author, channel=ctx.channel, content=content)  # type: ignore[arg-type]

        reminder.store(self.bot.redis_helper)
        reminder_md = cast(discord.Embed, reminder.as_markdown(ctx.author, ctx.channel, as_embed=True))  # type: ignore[arg-type]
        logger.info(f'Successfully created a new reminder for "{ctx.author.name}"')
        logger.debug(f'Reminder:\n{reminder.dump()}')

        confirm = await ConfirmMenu(f'Create reminder at `{reminder.trigger_dt.ctime()}` for `{content}`?').prompt(ctx)

        if not confirm:
            logger.info(f'Canceling reminder for {ctx.author.name} based on prompt response')
            return

        self.bot.scheduler.add_job(self._process_reminder, kwargs={'reminder': reminder, 'added_at': dt_now}, trigger='date',
                                   run_date=reminder.trigger_dt, id=reminder.redis_name)
        logger.info(f'Scheduled new reminder job at "{reminder.trigger_dt.ctime()}"')

        await ctx.send(f'Adding new reminder for {ctx.author.mention} at {reminder.trigger_dt.ctime()}`', embed=reminder_md)

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

        logger.info(f'{msg_out}. Requested in "{ctx.channel}" by "#{ctx.author.name}" on "{ctx.guild.name if ctx.guild else "None"}"')
        cnt = 0

        for rem in reminders:
            try:
                if not for_member and not rem.is_complete:
                    logger.info(f'Skipping pending reminder for "{rem.redis_name}" since no member was passed to "reminders clean" command')
                    continue

                logger.debug(f'Running hdel() on "{rem.redis_name}" for "{rem.member_name}"')
                with self.bot.redis_helper.wrapped_redis(f'hdel("reminders", "{rem.redis_name}")') as r_conn:
                    r_conn.hdel('reminders', rem.redis_name)

                sched_job = self.bot.scheduler.get_job(rem.redis_name)
                if sched_job:
                    logger.info(f'Removing scheduled job for reminder "{rem.redis_name}" at "{rem.trigger_dt.ctime()}"')
                    sched_job.remove()

                cnt += 1
            except Exception as ex:
                await ctx.send(f'Sorry {ctx.author.mention} but encountered an error attempting to delete reminders')
                logger.exception(f'Failure while attempting to delete reminders from Redis: {ex}')
                continue

        await ctx.send(f'{msg_out}... Removed #{cnt}. :smile:')

    @commands.command(name='when')
    async def when(self, ctx: commands.Context, when: FuzzyTimeConverter, *, use_tz: Optional[str] = None):
        logger.info(f'cmd: when. when -> "{when}", use_tz: "{use_tz}"')

        assert isinstance(when, FuzzyTime)

        if use_tz:
            if not Timezone.is_valid_timezone(use_tz):
                await ctx.send(f'Sorry {ctx.author.mention}, "{use_tz}" does not appear to be a valid timezone')
                return

            timezone = Timezone.build(use_tz)
            fuz_tz = FuzzyTime.build(provided_when=when.provided_when, created_time=datetime.now(timezone.timezone), use_timezone=timezone)
        else:
            fuz_tz = cast(FuzzyTime, when)

        await ctx.send(f'Resolved `{when}` -> ```\n{fuz_tz} (`{fuz_tz.resolved_time}`)\n```\n> use_tz: `{use_tz}`')

    @commands.guild_only()
    @reminders.command(name='lookup')
    async def lookup_reminder(self, ctx: commands.Context, target_member: discord.Member = None) -> None:
        pass
