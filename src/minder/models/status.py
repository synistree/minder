from __future__ import annotations

import logging

from dataclasses import dataclass, field
from datetime import datetime
from redisent.models import RedisEntry
from typing import Mapping, Any

from minder.errors import MinderError

logger = logging.getLogger(__name__)

StatusEntryActions: Mapping[str, str] = {
    'LOGON': 'Logged on',
    'LOGOFF': 'Logged off',
    'JOIN': 'Joined',
    'PART': 'Parted',
    'ERROR': 'Error',
    'DEBUG': 'Debug'
}


@dataclass
class StatusEntry(RedisEntry):
    redis_id: str = 'bot_status'

    timestamp: datetime = field(default_factory=datetime.now)
    action: str = field(default_factory=str)
    message: str = field(default_factory=str)

    context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.redis_name = str(f'{self.action}:{self.timestamp.timestamp()}')

        if self.action not in StatusEntryActions:
            if self.action.upper() not in StatusEntryActions:
                raise MinderError(f'Invalid status entry action: "{self.action}". Must be one of "{", ".join(StatusEntryActions)}"')

            self.action = self.action.upper()

    def __str__(self) -> str:
        return f'(StatusEntry -- {self.action}): {self.message}'

    def __repr__(self) -> str:
        attrs = f'action="{self.action}", timestamp="{self.timestamp.ctime()}", message="{self.message}"'

        if self.context:
            attrs = f'{attrs}, context="{self.context}"'

        return f'StatusEntry({attrs})'

    @classmethod
    def build(cls, action: str, message: str, context: Mapping[str, Any] = None, use_timestamp: datetime = None) -> StatusEntry:
        action = action.upper()
        if action not in StatusEntryActions:
            raise MinderError(f'Invalid action value provided while building status entry: {action}. Must be one of "{", ".join(StatusEntryActions)}"')

        ent_kwargs = {'action': action, 'message': message}

        if context:
            ent_kwargs['context'] = context

        if use_timestamp:
            ent_kwargs['timestamp'] = use_timestamp

        return StatusEntry(**ent_kwargs)
