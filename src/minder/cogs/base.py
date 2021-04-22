from __future__ import annotations

import discord
import logging

from discord.ext import commands
from typing import List, Type

logger = logging.getLogger(__name__)


class BaseCog(commands.Cog):
    _subclasses: List[Type[BaseCog]] = []

    def __init__(self, bot, *args, **kwargs) -> None:
        self.bot = bot
        super().__init__()

    @classmethod
    def __init_subclass__(cls) -> None:
        cls._subclasses.append(cls)

    @property
    def bot_ready(self) -> bool:
        return True if self.bot and self.bot.init_done else False

    async def check_ready_or_fail(self, ctx: commands.Context, send_response: bool = True) -> bool:
        if self.bot_ready:
            return True

        if send_response:
            author = ctx.author.mention if isinstance(ctx.author, discord.Member) and ctx.author.guild else ctx.author.name
            await ctx.send(f'Sorry {author}, bot is not done loading yet.. Try again in a few moments. :thinking_face:')

        return False
