import discord
import pytest
import redislite

from typing import Tuple, Optional

from minder.web.app import create_app
from minder.models import Reminder

pytest_plugins = ['pytest-flask-sqlalchemy']

tmp_redis = redislite.Redis()


@pytest.fixture(scope='function')
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


@pytest.fixture(scope='session')
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


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client

# Discord-related fixtures for faking data models


class FakeGuild(discord.Guild):
    id: int = 98765
    name: str = 'pytest-server'
    emojis: Tuple[discord.Emoji] = []
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
    discriminator: str = 69584
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
