from __future__ import annotations

import logging

from minder.cli import register_app_cli
from minder.config import Config
from minder.errors import MinderWebError
from minder.web.model import db

from flask import Flask, redirect, url_for, jsonify, request
from flask_bootstrap import Bootstrap, WebCDN
from flask_login import LoginManager
from flask_moment import Moment
from flask_pretty import Prettify

from redisent.common import RedisType
from redisent.helpers import RedisentHelper

from typing import Any, Mapping, Union

from werkzeug.exceptions import Unauthorized

moment = Moment()
logger = logging.getLogger(__name__)


class FlaskApp(Flask):
    """
    Minder Flask application

    This is a subclass of :py:cls:`flask.Flask` which automatically loads and configures the minder Flask application

    An instance of :py:cls:`redisent.helpers.RedisentHelper` as "redis_helper"
    """

    redis_helper: RedisentHelper

    def __init__(self, import_name: str, *args, hostname: str = None, port: str = None, use_reloader: bool = None,
                 overrides: Mapping[str, Any] = None, use_redis: RedisType = None, **kwargs) -> None:
        overrides = overrides or {}

        # Enforce setting "instance_relative_config" to True when setting up the Flask application
        kwargs['instance_relative_config'] = True

        # Set root template and static path
        kwargs['template_folder'] = 'templates'
        kwargs['static_folder'] = 'static'

        super().__init__(import_name, *args, **kwargs)

        self._hostname = hostname or Config.FLASK_HOST
        self._port = port or Config.FLASK_PORT
        self._use_reloader = use_reloader or Config.ENABLE_AUTORELOAD

        self.config.from_object('minder.config.Config')

        self.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        if overrides:
            for o_key, o_val in overrides.items():
                self.config[o_key] = o_val

        # Setup Flask plugins
        db.init_app(self)
        Prettify(self)
        Bootstrap(self)
        moment.init_app(self)

        self.login_manager = LoginManager()
        self.login_manager.login_view = 'app.login'
        self.login_manager.init_app(self)

        # Also register the correct JQuery version for use with Flask_Bootstrap
        self.extensions['bootstrap']['cdns']['jquery'] = WebCDN('//cdnjs.cloudflare.com/ajax/libs/jquery/3.5.1/')

        # Iterate through each blueprint and register it with the application
        from minder.web.blueprints.app import app_bp
        from minder.web.blueprints.api import api_bp

        self.register_blueprint(app_bp)
        self.register_blueprint(api_bp)

        # Similarly, replicates the functionality of the "error_handler" decorator
        # This is used to automatically redirect to "/login" if the user is not already
        # logged in (i.e. HTTP 401 error)
        self.register_error_handler(Unauthorized, self._handle_auth_error)

        # Register error handler for MinderWebError errors
        self.register_error_handler(MinderWebError, self._handle_app_error)

        # Register the Click CLI extensions from "minder.cli"
        register_app_cli(self)

        # Setup RedisentHelper
        pool = RedisentHelper.build_pool(Config.REDIS_URL)
        if use_redis:
            logger.info(f'Using provided Redis instance: {use_redis}')

        self.redis_helper = RedisentHelper(pool, use_redis=use_redis)

        # Finally, setup SQLAlchemy
        self.logger.info('Initalizing database tables..')

        with self.app_context():
            db.create_all()

        @self.login_manager.user_loader
        def load_user(user_id):
            from minder.web.model import User
            return User.query.get(int(user_id))

    def _handle_app_error(self, exception: MinderWebError = None):
        """
        Handle any other application errors that might arrise in the form of :py:exc:`MinderWebError` exceptions

        These should return "nice" JSON-ifyable results and an error log entry will be created recording the error
        """

        response = jsonify(exception.as_dict() if exception else {})
        response.status_code = exception.status_code if exception else 500
        err_message = f'Handling {response.status_code} error from "{request.remote_addr}" via "{request.url}"'

        if exception:
            err_message = f'{err_message}: {exception}'

        logger.error(err_message)
        return response

    def _handle_auth_error(self, exception: Unauthorized = None):
        """
        Default exception handler for "Unauthorized" exceptions which will trigger a HTTP 302 redirect to the
        login page

        The actual value of "exception" is ignored here since it is only registered for "Unauthorized" exceptions
        """

        return redirect(url_for('app.login'))

    def run(self, *args, **kwargs) -> None:
        """
        Wraps ``Flask.run`` to inject the correct value for ``use_reloader``, ``host`` and ``port``
        """

        kwargs['use_reloader'] = self._use_reloader
        kwargs['host'] = self._hostname
        kwargs['port'] = int(self._port)

        super().run(*args, **kwargs)


def create_app(hostname: str = None, port: Union[int, str] = None, use_reloader: bool = None, overrides: Mapping[str, Any] = None,
               use_redis: RedisType = None) -> FlaskApp:
    hostname = hostname or Config.FLASK_HOST
    port = str(port or Config.FLASK_PORT)

    return FlaskApp(__name__, hostname=hostname, port=port, use_reloader=use_reloader, overrides=overrides, use_redis=use_redis)