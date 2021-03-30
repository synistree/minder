import logging

from discord.ext import commands

from typing import List

logger = logging.getLogger(__name__)


class BaseCog(commands.Cog):
    bot: commands.Bot

    _subclasses: List[commands.Cog] = []

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._subclasses.append(cls)

    @property
    def bot_ready(self) -> bool:
        return self.bot and self.bot.init_done
