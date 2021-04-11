import logging
import traceback

from discord.ext import commands
from typing import Mapping, Optional

logger = logging.getLogger(__name__)


def get_stacktrace(from_exception: Exception = None) -> str:
    exc_info = traceback.format_exc(chain=True)

    if from_exception and hasattr(from_exception, '__traceback__'):
        exc_info = traceback.format_exception(type(from_exception), from_exception, from_exception.__traceback__)

    return ''.join(exc_info)


class MinderError(Exception):
    '''
    Base error class for all errors related to ``minder``
    '''

    message: str
    base_exception: Optional[Exception] = None

    def __init__(self, message: str, base_exception: Exception = None) -> None:
        super().__init__(message)

        self.message = message
        self.base_exception = base_exception

    def __sub_repr__(self) -> str:
        """
        Optional method for subclasses to extend the ``repr()`` attributes
        """

        return ''

    def __repr__(self) -> str:
        err_name = self.__class__.__qualname__

        repr_out = f'{err_name}(message="{self.message}"'

        if self.base_exception:
            repr_out += f', base_exception="{self.base_exception}"'

        sub_repr = self.__sub_repr__()
        if sub_repr:
            repr_out += f', {sub_repr}'

        repr_out += ')'

        return repr_out


class MinderWebError(MinderError):
    status_code: int
    message: str
    payload: Mapping

    base_exception: Optional[Exception]

    def __init__(self, message: str, status_code: int = None, payload: Mapping = None, base_exception: Exception = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code or 400
        self.payload = payload or {}
        self.base_exception = base_exception

        logger.info(f'Web Error: {message} (status_code: {status_code})')

        exc_out = get_stacktrace(self.base_exception)
        st_out = f'Stack trace:\n{exc_out}'

        if payload:
            st_out += f'\nPayload:\n{payload}'

        logger.info(st_out)

    def as_dict(self) -> Mapping:
        ret = self.payload.copy()
        ret['is_error'] = True
        ret['message'] = self.message
        return ret


class MinderBotError(MinderError):
    """
    Exception class for errors occuring within the bot
    """

    context: Optional[commands.Context] = None

    def __init__(self, message: str, base_exception: Exception = None, context: commands.Context = None) -> None:
        super().__init__(message)

        self.message = message
        self.context = context
        self.base_exception = base_exception

    def __sub_repr__(self) -> str:
        return f'context="{self.context}"'
