import click
import IPython
import os
import sys
import logging

from flask.cli import AppGroup, with_appcontext
from tabulate import tabulate

from minder.bot import build_bot
from minder.errors import get_stacktrace

logger = logging.getLogger(__name__)

user_cli = AppGroup('users', help='Manage web user database entries')

@user_cli.command('list', help='List current web users')
@with_appcontext
def list_users():
    from minder.web.model import User  # noqa: F401
    click.secho('Dumping current web users..', fg='cyan')

    tbl_out = []
    hdrs = ['ID', 'Username', 'Is Admin?', 'Enabled?']

    for usr in User.query.all():
        tbl_out.append([usr.id, usr.username, 'Yes' if usr.is_admin else 'No', 'Yes' if usr.enabled else 'No'])

    tbl = tabulate(tbl_out, headers=hdrs, tablefmt='fancy_grid')
    click.secho(tbl)

@user_cli.command('add', help='Add a new web user')
@click.option('-u', '--username', required=True, help='New username to create')
@click.option('-p', '--password-hash', default=None, help='Optionally provide password hash as argument')
@click.option('--admin/--not-admin', is_flag=True, default=False, help='Controls if the new user will be an administrative user')
@click.option('--enabled/--disabled', is_flag=True, default=True, help='If set, enable user otherwise user will be disabled')
@with_appcontext
def add_user(username, password_hash, admin, enabled):
    from minder.web.model import db, User  # noqa: F401

    if User.query.filter_by(username=username).count() > 0:
        click.secho(f'Error: Username "{username}" already exists in database', fg='red')
        sys.exit(1)

    if not password_hash:
        password_hash = click.prompt('Password (no echo)', hide_input=True, value_proc=User.generate_password)

        if not password_hash:
            click.secho('Error: No password provided. Aborting.', fg='red')
            sys.exit(2)
    else:
        if not password_hash.startswith('pbkdf2:sha256:'):
            click.secho('Error: It appears the password hash provided is not valid (must start with "pbkdf2:sha256:")', fg='red')
            sys.exit(3)

    click.secho(f'Creating new user entry for "{username}" (admin: {admin}, enabled: {enabled})', fg='cyan')
    
    usr = User(username=username, password_hash=password_hash, is_admin=admin, enabled=enabled)

    db.session.add(usr)
    db.session.commit()

    click.secho(f'Successfully added new user entry for "{username}" in database.', fg='green')

@user_cli.command('update', help='Update user parameters in database')
@click.option('-u', '--username', required=True, help='Username to update')
@click.option('-p', '--password-hash', default=None, help='If provided, use this password hash as the new user password')
@click.option('--enable-admin/--disable-admin', is_flag=True, default=None, help='If provided, update admin status')
@click.option('--enable-user/--disable-user', is_flag=True, default=None, help='If provided, update enabled status')
@click.option('--update-password', is_flag=True, default=None, help='If provided, prompt for new password to use')
@with_appcontext
def update_user(username, password_hash, enable_admin, enable_user, update_password):
    from minder.web.model import db, User  # noqa: F401

    usr = User.query.filter_by(username=username).first()

    if not usr:
        click.secho(f'Error: Username "{username}" does not already exist in database', fg='red')
        sys.exit(1)

    if password_hash:
        if not password_hash.startswith('pbkdf2:sha256:'):
            click.secho('Error: It appears the password hash provided is not valid (must start with "pbkdf2:sha256:")', fg='red')
            sys.exit(2)
    elif update_password:
        password_hash = click.prompt('Password (no echo)', hide_input=True, value_proc=User.generate_password)

        if not password_hash:
            click.secho('Error: No password provided. Aborting.', fg='red')
            sys.exit(3)

    usr_changed = False

    if password_hash:
        click.secho(f'-> Updating "{username}" password', fg='cyan')
        usr.password_hash = password_hash
        usr_changed = True
    
    if enable_admin is not None:
        click.secho(f'-> Setting "{username}" admin status: {enable_admin}', fg='cyan')
        usr.is_admin = enable_admin
        usr_changed = True

    if enable_user is not None:
        click.secho(f'-> Setting "{username}" enable status: {enable_user}', fg='cyan')
        usr.enabled = enable_user
        usr_changed = True

    if not usr_changed:
        click.secho(f'Warning: No changes requested for "{username}"...', fg='yellow')
        return
    
    db.session.commit()
    click.secho(f'Successfully updated "{username}"')


@user_cli.command('delete', help='Delete user from database')
@click.option('-u', '--username', required=True, help='Target username to delete')
@with_appcontext
def delete_user(username):
    from minder.web.model import db, User  # noqa: F401

    usr = User.query.filter_by(username=username).first()

    if not usr:
        click.secho(f'Error: Username "{username}" does not exist in database', fg='red')
        sys.exit(1)

    click.secho(f'Attempting to delete user "{username}" from database...', fg='cyan')

    if not click.confirm(f'Are you sure you want to delete "{username}" (ID: {usr.id}) from the database?', default='Y'):
        click.secho(f'Bailing out based on user response.', fg='yellow')
        sys.exit(2)

    db.session.delete(usr)
    db.session.commit()

    click.secho(f'Sucessfully deleted user "{username}" from database', fg='green')


def register_app_cli(app):
    @app.cli.command('ipy-shell', help='IPython shell for working within the Flask context')
    @with_appcontext
    def ipy_shell():
        from minder.web.model import db, User  # noqa: F401
        IPython.embed(header='Welcome to the minder IPython shell', colors='linux', using='asyncio')

    app.cli.add_command(user_cli)


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
