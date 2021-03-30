import logging

from sqlalchemy import Column, String, Integer, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from typing import List

logger = logging.getLogger(__name__)


Base = declarative_base()


class UserSetting(Base):
    __tablename__ = 'user_settings'
    __table_args__ = {'sqlite_autoincrement': True}

    SETTING_TYPES: List[str] = ['str', 'int', 'float', 'bool']

    id = Column(Integer, primary_key=True)

    setting_name = Column(String, nullable=False, unique=True)
    setting_type = Column(String, Enum(*SETTING_TYPES), default='str')
    default_value = Column(String, default=None)

    setting_entries = relationship('UserSettingEntry', back_populates='parent')


class UserSettingEntry(Base):
    __tablename__ = 'user_setting_entries'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, nullable=False)
    guild_id = Column(Integer, nullable=False)

    setting_id = Column(Integer, ForeignKey('user_settings.id'))
    parent = relationship('UserSetting', back_populates='entries')
