from __future__ import annotations

import logging

from typing import List, Mapping, Any, Optional
from flask_sqlalchemy import SQLAlchemy, Model
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from minder.errors import MinderError

logger = logging.getLogger(__name__)
ModelMapping = Mapping[str, Any]


class SAModel(Model):
    @classmethod
    def get_private_columns(cls) -> List[str]:
        return []

    @classmethod
    def get_column_names(cls, exclude_private: bool = True) -> List[str]:
        excluded = cls.get_private_columns() if exclude_private else []
        return list([attr for attr in cls._sa_class_manager.keys() if not attr.startswith('_') and attr not in excluded])

    @classmethod
    def has_column(cls, name: str) -> bool:
        return name in cls.get_column_names(exclude_private=True)

    def dump(self, exclude_private: bool = True) -> ModelMapping:
        return {attr: getattr(self, attr) for attr in self.get_column_names(exclude_private=exclude_private)}

    @classmethod
    def model_name(cls) -> str:
        return cls.__class__.__qualname__

    @classmethod
    def from_dict(cls, model_dict: ModelMapping) -> SAModel:
        column_names = cls.get_column_names(exclude_private=True)
        model_kwargs = {attr: val for attr, val in model_dict.items() if attr in column_names}

        return cls(**model_kwargs)

    @classmethod
    def get_by(cls, attr_name: str, value: Any) -> Optional[SAModel]:
        if not cls.has_column(attr_name):
            raise MinderError(f'Cannot fetch "{cls.model_name()}" by "{attr_name}": No such column')

        qry = cls.query.filter_by(attr_name=value)
        cnt = qry.count()

        if cnt > 1:
            logger.warning(f'Request to fetch "{cls.model_name()}" by "{attr_name}" found #{cnt} results. Returning first match')

        return qry.first()

    def __repr__(self) -> str:
        attrs = ', '.join([f'{attr}="{val}"' for attr, val in self.dump(exclude_private=True).items()])
        return f'{self.model_name()}({attrs})'


db = SQLAlchemy(model_class=SAModel)


class User(db.Model, UserMixin):  # type: ignore[name-defined]
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return self.enabled and self.validate_password(password, self.password_hash)

    @classmethod
    def get_private_columns(cls) -> List[str]:
        return ['password_hash']

    @classmethod
    def validate_password(cls, raw_password: str, password_hash: str) -> bool:
        if check_password_hash(password_hash, raw_password):
            return True

        return False

    @classmethod
    def generate_password(cls, raw_password: str) -> str:
        new_pw: str = generate_password_hash(raw_password)
        return new_pw

    @classmethod
    def build(cls, username: str, password: str, enabled: bool = True, is_admin: bool = False) -> User:
        pw_hash = password if password.startswith('pbkdf2:sha256:') else User.generate_password(password) 
        return User(username=username, password_hash=pw_hash, enabled=enabled, is_admin=is_admin)
