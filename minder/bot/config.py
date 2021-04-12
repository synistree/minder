from __future__ import annotations

import logging
import os.path
import yaml

from dataclasses import dataclass, asdict
from typing import Any, Optional, Mapping, List

from minder.errors import MinderError

logger = logging.getLogger(__name__)


@dataclass
class BotConfig:
    """
    Class for loading user and guild configuration for the bot to use

    This class is reponsible for loading the default guild behavior, registering static users and otherwise
    providing per-guild configuration details like which channel the bot should dump messages into as well as
    if errors should included traceback details also
    """

    admins: List[int]
    extended_errors: bool
    ignore_other_guilds: bool

    users: Mapping
    guilds: Mapping

    def as_dict(self, only_guilds: List[int] = None) -> Mapping[str, Any]:
        if not only_guilds:
            return asdict(self)

        only_guilds = [int(g_id) for g_id in only_guilds]

        flds = {f_name: getattr(self, f_name) for f_name in ['admins', 'extended_errors', 'ignore_other_guilds']}

        glds = {g_id: g_ent for g_id, g_ent in self.guilds.items() if g_id in only_guilds}
        usrs = {u_id: u_ent for u_id, u_ent in self.users.items() if u_id in only_guilds}

        flds['guilds'] = glds
        flds['users'] = usrs

        return flds

    def __init__(self, admins: List[int] = None, extended_errors: bool = False, ignore_other_guilds: bool = True, users: Mapping[str, Any] = None,
                 guilds: Mapping[str, Any] = None) -> None:
        self.admins = admins or []
        self.extended_errors = extended_errors
        self.ignore_other_guilds = ignore_other_guilds

        self.users = users or {}
        self.guilds = guilds or {}

    def get_user(self, username: str = None, user_id: int = None, throw_error: bool = False):
        if username:
            usr = self._user_by_name(username)
            if usr:
                return usr

            target = f'"username": {username}'
        elif user_id:
            user_id = user_id

            if user_id in self.users:
                return self.users[user_id]

            target = f'"user_id": {user_id}'
        else:
            raise MinderError('Unable to determine what user to fetch. Neither "username" nor "user_id" were provided')

        err_message = f'Unable to find configured user by {target}: Not found'

        if throw_error:
            raise MinderError(err_message)

        logger.warning(err_message)
        return None

    def get_user_setting(self, user_id: int, name: str, throw_error: bool = False, **kwargs) -> Optional[Any]:
        if 'default' in kwargs:
            has_default = True
            default = kwargs['default']
        else:
            has_default = False
            default = None

        if user_id not in self.users:
            err_message = f'Requested setting for "{name}" of non-existent user with ID "{user_id}"'

            if throw_error:
                raise MinderError(err_message)

            logger.warning(err_message)
            return None

        usr = self.get_user(user_id=user_id, throw_error=False)

        if name in usr:
            return usr[name]

        if has_default:
            return default

        err_message = f'Requested missing setting for "{name}" from user "{usr["name"]}" (ID: {user_id})'

        if throw_error:
            raise MinderError(err_message)

        logger.warning(err_message)
        return None

    def _user_by_name(self, username: str):
        for usr in self.users.values():
            if usr['name'] == username:
                return usr

        return None

    def has_user(self, username: str) -> bool:
        if self._user_by_name(username):
            return True

        return False

    def get_guild(self, name: str = None, guild_id: int = None, throw_error: bool = False):
        if not name and not guild_id:
            raise MinderError('Unable to determine what guild to fetch. Neither "name" nor "guild_id" were provided')

        if name:
            gld = self._guild_by_name(name)

            if gld:
                return gld

            target = f'"name": {name}'
        else:
            if guild_id in self.guilds:
                return self.guilds[guild_id]

            target = f'"guild_id": {guild_id}'

        err_message = f'Unable to find configured guild by {target}: Not found'

        if throw_error:
            raise MinderError(err_message)

        logger.warning(err_message)
        return None

    def _guild_by_name(self, name: str):
        for gld in self.guilds.values():
            if gld['name'] == name:
                return gld

        return None

    def has_guild(self, name: str) -> bool:
        if self._guild_by_name(name):
            return True

        return False

    @classmethod
    def load(cls, yaml_file: str) -> BotConfig:
        if not os.path.exists(yaml_file):
            raise MinderError(f'No such bot config YAML file: "{yaml_file}"')

        try:
            with open(yaml_file, 'rt') as f:
                yaml_cfg = yaml.safe_load(f)
        except yaml.error.YAMLError as ex:
            raise MinderError(f'Error loading bot config YAML from "{yaml_file}": {ex}') from ex
        except Exception as ex:
            raise MinderError(f'General error while loading bot config from "{yaml_file}": {ex}') from ex

        cls_kwargs = {}

        if 'defaults' in yaml_cfg:
            def_cfg = yaml_cfg['defaults']

            if 'admins' in def_cfg:
                cls_kwargs['admins'] = def_cfg['admins']

            if 'extended_errors' in def_cfg:
                cls_kwargs['extended_errors'] = def_cfg['extended_errors']

            if 'ignore_other_guilds' in def_cfg:
                cls_kwargs['ignore_other_guilds'] = def_cfg['ignore_other_guilds']

        if 'admins' in yaml_cfg:
            cls_kwargs['admins'] = yaml_cfg['admins']

        if 'users' in yaml_cfg:
            cls_kwargs['users'] = yaml_cfg['users']

        if 'guilds' in yaml_cfg:
            cls_kwargs['guilds'] = yaml_cfg['guilds']

        return cls(**cls_kwargs)

    def save(self, yaml_file: str):
        yaml_cfg = {'defaults': {'admins': self.admins, 'extended_errors': self.extended_errors, 'ignore_other_guilds': self.ignore_other_guilds},
                    'users': self.users,
                    'guilds': self.guilds}

        try:
            with open(yaml_file, 'wt') as f:
                yaml.safe_dump(yaml_cfg, f, indent=2, default_flow_style=False)

        except yaml.error.YAMLError as ex:
            raise MinderError(f'Error saving bot config YAML to "{yaml_file}": {ex}') from ex
        except Exception as ex:
            raise MinderError(f'General error while saving bot config to "{yaml_file}": {ex}') from ex
