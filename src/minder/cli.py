import click
import IPython
import os
import logging

from minder.bot import build_bot
from minder.errors import get_stacktrace

logger = logging.getLogger(__name__)


def register_app_cli(app):
    @app.cli.command('ipy-shell', help='IPython shell for working within the Flask context')
    def ipy_shell():
        app.make_shell_context()
        from minder.web.model import db, User  # noqa: F401
        IPython.embed(header='Welcome to the minder IPython shell', colors='linux', using='asyncio')


@click.group(name='minder', context_settings={'help_option_names': ['-h', '--help']})
@click.option('-D', '--debug', is_flag=True, default=False, help='Enable more verbose debugging output')
@click.pass_context
def run_cli(ctx: click.Context, debug: bool = False):
    ctx_obj = ctx.ensure_object(dict)
    ctx_obj['debug'] = debug

    if debug:
        click.secho('Enabling debugging output...', fg='blue')
        os.environ['DEBUG'] = os.environ['ENABLE_DEBUG'] = 'True'
        logger.setLevel(logging.DEBUG)
        discord_log = logging.getLogger('discord')

        if discord_log:
            discord_log.setLevel(logging.DEBUG)


@run_cli.command(name='run-bot')
@click.option('-T', '--token', default=None, help='Optionally provide bot token')
def run_bot(token: str = None):
    click.secho('Starting minder bot...', fg='green')

    try:
        build_bot(use_token=token, start_bot=True)
    except Exception as ex:
        exc_info = get_stacktrace(ex)
        click.secho(f'Error running bot: {ex}', fg='red')
        click.secho(f'Stack Trace:\n{"".join(exc_info)}', fg='cyan')
        raise click.Abort()
    else:
        click.secho('Bot finished :)', fg='green')


@run_cli.command(name='run-web')
@click.option('-H', '--host', default='0.0.0.0', help='Hostname for Flask to listen on (default is any IP, "0.0.0.0")')
@click.option('-P', '--port', type=int, default=5000, help='Port for Flask to listen on (default is 5000)')
@click.option('--use-reloader/--no-reloader', is_flag=True, default=False, help='Enable or disable automatic reloading by Flask (default is off)')
@click.pass_context
def run_web(ctx: click.Context, host: str, port: int, use_reloader: bool = False):
    from minder.web.app import create_app

    debug = ctx.obj.get('debug', False)

    try:
        app = create_app(hostname=host, port=port, use_reloader=use_reloader)
    except Exception as ex:
        exc_info = get_stacktrace(ex)
        click.secho(f'Error creating minder Flask application: {ex}', fg='red')
        click.secho(f'Stack Trace:\n{"".join(exc_info)}', fg='cyan')
        raise click.Abort()

    click.secho('Flask application created. Starting now...', fg='green')

    try:
        app.run(debug=debug)
    except Exception as ex:
        exc_info = get_stacktrace(ex)
        click.secho(f'Error running minder Flask application: {ex}', fg='red')
        click.secho(f'Stack Trace:\n{"".join(exc_info)}', fg='cyan')
        raise click.Abort()

    click.secho('Flask application finished :)', fg='green')


__all__ = ['register_app_cli', 'run_cli']
