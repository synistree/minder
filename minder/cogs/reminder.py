import logging

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
        reminders = []

        with self.bot.redis_helper.wrapped_redis('hkeys("reminders")') as r_conn:
            rem_keys = r_conn.hkeys('reminders')

        if not rem_keys:
            return []

        for rem_id in rem_keys:
            with self.bot.redis_helper.wrapped_redis(f'hget("reminders", "{rem_id}")') as r_conn:
                rem = Reminder.fetch(self.bot.redis_helper, redis_id='reminders', redis_name=rem_id)
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
        await ctx.send(f'Adding new reminder for {ctx.author.mention}', embed=reminder_md)
