import discord

from discord.ext import commands
from discord.ext import menus

from minder.utils import EMOJIS


class ConfirmMenu(menus.Menu):
    prompt_message: discord.Message
    result: bool

    def __init__(self, message: discord.Message, timeout: float = 30.0, delete_after: bool = True) -> None:
        super().__init__(timeout=timeout, delete_message_after=delete_after)
        self.prompt_message = message
        self.result = None

    async def send_initial_message(self, ctx: commands.Context, channel: discord.ChannelType) -> None:
        return await channel.send(self.prompt_message)

    @menus.button(EMOJIS[':white_check_mark:'])
    async def do_confirm(self, payload):
        self.result = True
        self.stop()

    @menus.button(EMOJIS[':heavy_multiplication_x:'])
    async def do_deny(self, payload):
        self.result = False
        self.stop()

    async def prompt(self, ctx: commands.Context) -> bool:
        await self.start(ctx, wait=True)
        return self.result or False
