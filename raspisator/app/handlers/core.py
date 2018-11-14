
from abc import ABCMeta, abstractmethod

class HandleMiddleware(metaclass=ABCMeta):
    def __init__(self, bot, usersmodel=None, studiesmodel=None, celery=None, *, debug=False):
        self.bot = bot
        self.u = usersmodel
        self.s = studiesmodel
        self.broker = celery
        self._add_handlers()

    @abstractmethod
    def _add_handlers(self):
        pass
