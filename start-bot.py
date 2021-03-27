#!/usr/bin/env python3.8

from minder.bot import build_bot
from minder.config import Config


if __name__ == '__main__':
    bot = build_bot(start_bot=False)
    bot.run(Config.BOT_TOKEN)
