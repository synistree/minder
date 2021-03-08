import discord
import logging

from discord.ext import commands
from typing import List

from minder.models import Reminder

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
                rem = Reminder.fetch(self.bot.redis_helper, 'reminders', rem_id)
                reminders.append(rem)

        return reminders

    @commands.command(name='reminders')
    async def reminders(self, ctx: commands.Context, member: discord.Member = None) -> None:
        if not self.bot.init_done:
            await ctx.send(f'Sorry {ctx.author.mention}, bot is not done loading yet..')
            return

        reminders = self._get_reminders(member_id=member.id if member else None)

        await ctx.send(f'Hey {ctx.author.mention}, found #{len(reminders)} reminders..')
