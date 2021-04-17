from __future__ import annotations

import logging
import os.path
import yaml

from dataclasses import dataclass, field
from redisent.models import RedisEntry
from typing import Optional, Any, MutableMapping

from minder.errors import MinderError

logger = logging.getLogger(__name__)


@dataclass
class UserSettings(RedisEntry):
    redis_id: str = 'user_settings'

    guild_id: Optional[int] = field(default=None)
    member_id: int = field(default_factory=int)

    settings: MutableMapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.redis_name = str(self.member_id)

    def set_value(self, name: str, value: Any) -> bool:
        has_value = True if self.has_setting(name) else False
        self.settings[name] = value
        return has_value

    def has_setting(self, name: str) -> bool:
        return name in self.settings

    def get_value(self, name: str, throw_error: bool = True, **kwargs) -> Optional[Any]:
        if self.has_setting(name):
            return self.settings[name]

        if 'default' in kwargs:
            return kwargs['default']

        if throw_error:
            raise MinderError(f'Invalid user setting value requested: "{name}"')

        return None

    @classmethod
    def from_yaml(cls, yaml_file: str) -> UserSettings:
        yaml_file = os.path.abspath(os.path.expanduser(yaml_file))

        if not os.path.exists(yaml_file):
            raise MinderError(f'Unable to find user settings file "{yaml_file}"')

        try:
            with open(yaml_file, 'rt') as f:
                yaml_cfg = yaml.safe_load(f)
        except Exception as ex:
            raise MinderError(f'Failure parsing user settings from "{yaml_file}": {ex}') from ex

        member_id = yaml_cfg['member_id']
        guild_id = yaml_cfg.get('guild_id', None)
        return UserSettings(guild_id=guild_id, member_id=member_id, settings=yaml_cfg['settings'])
