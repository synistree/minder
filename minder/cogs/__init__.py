from minder.cogs.reminder import ReminderCog
from minder.cogs.errors import ErrorHandlerCog

all_cogs = [ReminderCog, ErrorHandlerCog]

__all__ = ['ReminderCog', 'ErrorHandlerCog', 'all_cogs']
