import discord
import pytest

from minder.bot import build_bot


def test_start_bot():
    bot = build_bot(start_bot=False)
    with pytest.raises(discord.errors.LoginFailure):
        bot.run('asdf')
