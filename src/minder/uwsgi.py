import logging

from minder.bot import build_bot
from minder.config import Config
from minder.web.app import create_app

logger = logging.getLogger(__name__)

app = create_app()


def start_bot():
    logger.info('Starting minder Bot under uWSGI...')
    bot = build_bot(start_bot=True)
    loop = bot.loop

    try:
        loop.run_in_executor(None, app.run, kwargs={'reload': False, 'eager_loader': False})
        loop.run_until_complete(bot.start(Config.BOT_TOKEN))
        logger.info('Bot finished, exiting')
    except KeyboardInterrupt:
        logger.info('CTRL-C encountered, logging out and cleaning up')
        loop.run_until_complete(bot.logout())
        logger.info('Bot logout complete')
    finally:
        logger.info('Loop closing..')
        loop.close()
        logger.info('Loop closed, exiting.')


__all__ = ['app', 'start_bot']
