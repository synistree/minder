import os
import discord
import pytest
import logging
import redislite.client

from sqlalchemy.engine.url import make_url
from typing import Optional

# The "ENV_PATH" environment variable needs to be set prior to pulling in the "minder.*" dependencies
#
# Generally, with tox, this will be covered by the "tox-envfile" plugin but for good measure adding
# here as well.
#
# Finally all env files should point to the ".devdata.env" symlink in the root of the repository. This
# symlink points to the "dot_env.example" file.
os.environ['ENV_PATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '../.devdata.env'))

from minder.web.app import create_app  # noqa: E402
from minder.models import Reminder  # noqa: E402

pytest_plugins = ['pytest-flask-sqlalchemy']

tmp_redis = redislite.client.Redis()


@pytest.fixture
def session(db, request):
    connection = db.engine.connect()
    transaction = connection.begin()

    options = dict(bind=connection, binds={})
    session = db.create_scoped_session(options=options)

    db.session = session

    def teardown():
        transaction.rollback()
        connection.close()
        session.remove()

    request.addfinalizer(teardown)
    return session


@pytest.fixture
def app(request):
    cfg_override = {'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:', 'TESTING': True,
                    'WTF_CSRF_ENABLED': False}
    return create_app(overrides=cfg_override, use_redis=tmp_redis)


@pytest.fixture
def db(app):
    from minder.web.model import db

    with app.app_context():
        db.create_all()
        yield db
        db.drop_all()
        db.session.commit()

        eng_url = make_url(app.config['SQLALCHEMY_DATABASE_URI'])
        db_url = db.engine.url
        assert eng_url == db.engine.url, f'Config SQLALchemy URL does not match config. Expected "{eng_url}", found "{db_url}"'


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture
def cli_runner(app):
    return app.test_cli_runner()


# Discord-related fixtures for faking data models


class FakeGuild(discord.Guild):
    id: int = 98765
    name: str = 'pytest-server'
    owner_id: int = 12345
    icon: Optional[str] = None

    def __init__(self, **kwargs):
        for attr, val in kwargs.items():
            setattr(self, attr, val)


@pytest.fixture
def fake_guild():
    return FakeGuild()


class FakeMember(discord.Member):
    guild: discord.Guild

    id: int = 12345
    name: str = 'pytest'
    discriminator: str = '12345'
    avatar: Optional[str] = None
    bot: bool = False
    system: bool = False

    def __init__(self, guild, **kwargs):
        for attr, val in kwargs.items():
            setattr(self, attr, val)

        self.guild = guild


@pytest.fixture
def fake_member(fake_guild):
    return FakeMember(guild=fake_guild)


class FakeTextChannel(discord.TextChannel):
    guild: discord.Guild

    id: int = 54321
    name: str = 'pytesting'
    topic: str = 'pytest fake channel'
    nsfw: bool = False

    def __init__(self, guild, **kwargs):
        for attr, val in kwargs.items():
            setattr(self, attr, val)

        self.guild = guild


@pytest.fixture
def fake_text_channel(fake_guild):
    return FakeTextChannel(fake_guild)


class FakeUser(discord.User):
    id: int = 23456
    name: str = 'pytest'
    discriminator: str = '69584'
    avatar: Optional[str] = None
    bot: bool = False
    system: bool = False

    def __init__(self, **kwargs):
        for attr, val in kwargs.items():
            setattr(self, attr, val)


@pytest.fixture
def fake_user():
    return FakeUser()


class FakeDMChannel(discord.DMChannel):
    recipient: discord.User
    id: int = 76543

    def __init__(self, recipient, **kwargs):
        for attr, val in kwargs.items():
            setattr(self, attr, val)

        self.recipient = recipient


@pytest.fixture
def fake_dm_channel(fake_user):
    return FakeDMChannel(recipient=fake_user)


@pytest.fixture
def fake_channel_reminder(fake_member, fake_text_channel):
    return Reminder.build(trigger_time='in 5 minutes', member=fake_member, content='pytest test channel reminder', channel=fake_text_channel)


@pytest.fixture
def fake_dm_reminder(fake_member, fake_dm_channel):
    return Reminder.build(trigger_time='in 5 minutes', member=fake_member, content='pytest test DM reminder', channel=fake_dm_channel)


# Flake8 errors in the logs during testing are really not helpful and very verbose
# same with SQLAlchemy engine entries
for mod_cls in ['flake8.plugins.manager', 'sqlalchemy.engine.Engine']:
    logging.getLogger(mod_cls).setLevel(logging.WARNING)
