from __future__ import annotations

import logging

from typing import List
from flask_sqlalchemy import SQLAlchemy, Model
from flask_login import UserMixin

from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)


class SAModel(Model):
    @classmethod
    def get_column_names(cls, exclude_private: bool = True) -> List[str]:
        return list([attr for attr in cls._sa_class_manager.keys() if not exclude_private and not attr.startswith('_')])


db = SQLAlchemy(model_class=SAModel)


class User(db.Model, UserMixin):
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
    def validate_password(cls, raw_password: str, password_hash: str) -> bool:
        return check_password_hash(password_hash, raw_password)

    @classmethod
    def generate_password(cls, raw_password: str) -> str:
        return generate_password_hash(raw_password)
