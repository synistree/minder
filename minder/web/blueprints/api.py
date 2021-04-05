import logging

from flask import Blueprint

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')
