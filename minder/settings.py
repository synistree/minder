from __future__ import annotations

import logging

from redisent.helpers import RedisentHelper
from typing import Any, List, Mapping, Optional

from minder.errors import MinderError
from minder.utils import Timezone

logger = logging.getLogger(__name__)


class SettingsHandler:
    manager: SettingsManager

    def __init__(self, manager: SettingsManager) -> None:
        self.manager = manager

    @classmethod
    def get_handled_settings(cls) -> List[str]:
        """
        Returns a list of setting names that are handled by this provided

        This method is used to quickly enumerate which settings handler is responsible for a given setting name
        """

        raise NotImplementedError('Instances of SettingsHandler must implement the "get_handled_settings" method')

    @classmethod
    def get_handler_name(cls) -> str:
        """
        Property that returns a unique name for this handler
        """

        raise NotImplementedError('Instances of SettingsHandler must implement the "handler_name" property')

    @property
    def handler_name(self) -> str:
        return self.get_handler_name()

    @property
    def handled_settings(self) -> List[str]:
        return self.get_handled_settings()

    @property
    def redis_helper(self) -> RedisentHelper:
        return self.manager.redis_helper

    def can_handle_setting(self, name: str) -> bool:
        """
        Method for determining if this ``SettingsHandler`` can process the provided setting based on the name

        Each instance of ``SettingsHandler`` is called while attempting to process user settings and any handler
        which returns ``True`` here will be called to process the provided setting.

        :param name: name of the setting to check if this handler can process
        :returns: if this handler supports the setting for ``name``, a value of ``True`` is returned. otherwise,
                  the value ``False`` is returned.
        """

        return name in self.handled_settings

    def process_setting(self, name: str, value: Any) -> Optional[Any]:
        """
        Handler for actually processing supported settings

        If the :py:func:`SettingsHandler.can_handle_setting` method returns ``True``, this method
        can be called to load and process this setting.

        If this handler cannot process the provided setting for ``name``, an exception will be raised.

        The return value from this method will be the fully processed setting value.

        :param name: name of the setting to process
        :param value: value to process for this setting
        :returns: processed setting value, if any
        """

        raise NotImplementedError('SettingsHandler instances must implement the "process_setting" method')


class TimezoneSetting(SettingsHandler):
    @classmethod
    def get_handled_settings(self) -> List[str]:
        return ['timezone']

    @classmethod
    def get_handler_name(self) -> str:
        return 'Timezone'

    def process_setting(self, name: str, value: str) -> Timezone:
        if name not in self.handled_settings:
            raise MinderError(f'Unable to process setting for "{name}" (not supported)')

        return Timezone.build(value)


class AdminSetting(SettingsHandler):
    @classmethod
    def get_handled_settings(self) -> List[str]:
        return ['admin_channels', 'admins']

    @classmethod
    def get_handler_name(self) -> str:
        return 'Admin'

    def process_setting(self, name: str, value):
        if name not in self.handled_settings:
            raise MinderError(f'Unable to process setting for "{name}" (not supported)')

        return self.redis_helper.get('settings', redis_name=name)


class SettingsManager:
    redis_helper: RedisentHelper
    handlers: Mapping[str, SettingsHandler]
    loaded_settings: Mapping[str, Any]

    def get_all_settings(self) -> Mapping[str, List[str]]:
        """
        Build a mapping of all supported handlers and settings
        """

        all_ents = {}

        for h_name, handler in self.handlers.items():
            for c_setting in handler.handled_settings:
                all_ents[c_setting] = handler

        return all_ents

    def __init__(self, redis_helper: RedisentHelper) -> None:
        self.redis_helper = redis_helper
        self.handlers = {}
        self.loaded_settings = {}

        for cls in SettingsHandler.__subclasses__():
            cur_cls = cls(self)
            for name in cur_cls.handled_settings:
                if name in self.handlers:
                    found_handler = self.handlers[name].handler_name
                    cur_handler = cur_cls.handler_name
                    raise MinderError(f'Found existing handler for "{name}" in handlers. Existing handler was "{found_handler}", this is "{cur_handler}"')

                self.handlers[name] = cur_cls

    def process_settings(self, settings: Mapping[str, Any]) -> bool:
        self.loaded_settings = {}
        any_failed = False

        for s_name, s_value in settings.items():
            if s_name not in self.handlers:
                logger.warning(f'Ignoring unsupported setting for "{s_name}" with value "{s_value}" (no handler found)')
                any_failed = True
                continue

            final_value = self.handlers[s_name].process_setting(s_name, s_value)
            self.loaded_settings[s_name] = final_value

            logger.debug(f'Successfully loaded setting for "{s_name}" with value "{final_value}"')

        return not any_failed

    def get_settings(self, handler_name: str, setting_name: str = None, throw_error: bool = True) -> Optional[Any]:
        if handler_name not in self.handlers:
            err_message = f'Unable to find settings handler for "{handler_name}"'

            if throw_error:
                raise MinderError(err_message)

            logger.error(err_message)
            return None

        hdr = self.handlers[handler_name]

        if setting_name:
            if not hdr.can_handle_setting(setting_name):
                err_message = f'No such setting "{setting_name}" found in handler "{handler_name}"'

                if throw_error:
                    raise MinderError(err_message)

                logger.error(err_message)
                return None

            settings = [setting_name]
        else:
            settings = hdr.handled_settings

        # TODO: Fix this
        return settings
