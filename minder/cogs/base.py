import logging

from discord.ext import commands
from typing import List

from minder.bot.checks import is_admin

logger = logging.getLogger(__name__)


class BaseCog(commands.Cog, name='base'):
    bot: commands.Bot

    _subclasses: List[commands.Cog] = []

    def __init__(self, bot: commands.Bot, *args, **kwargs) -> None:
        super().__init__()
        self.bot = bot

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._subclasses.append(cls)

    @property
    def bot_ready(self) -> bool:
        return self.bot and self.bot.init_done

    async def check_ready_or_fail(self, ctx: commands.Context, send_response: bool = True) -> bool:
        if self.bot_ready:
            return True

        if send_response:
            author = ctx.author.mention if ctx.author.guild else ctx.author.name
            await ctx.send(f'Sorry {author}, bot is not done loading yet.. Try again in a few moments. :thinking_face:')

        return False
