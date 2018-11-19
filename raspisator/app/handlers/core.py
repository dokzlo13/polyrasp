
from abc import ABCMeta, abstractmethod

class HandleMiddleware(metaclass=ABCMeta):
    def __init__(self, bot, usersmodel=None, studiesmodel=None, celery=None, cache=None, *, debug=False):
        self.bot = bot
        self.u = usersmodel
        self.s = studiesmodel
        self.broker = celery
        self.cache = cache
        self._add_handlers()

    @abstractmethod
    def _add_handlers(self):
        pass

    def log_wrapper(self, fun):
        def decor(message):
            # print("User {0} send {1}".format(message.from_user.id, message.text))
            return fun(message)
        return decor
