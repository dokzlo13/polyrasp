
from functools import partial
from telebot import types
# from raspisator.bot import *

from .templates import main_menu_button, back_button


class Retry(Exception):
    pass

def decor(method=None):
    # If called without method, we've been called with optional arguments.
    # We return a decorator with the optional arguments filled in.
    # Next time round we'll be decorating method.
    if method is None:
        return partial(decor)

    class wrapper:
        def __init__(self, method):
            self.method = method
            self.main_menu = None
            self.bot = None
            self.markup = None
            self._next = None
            self._previous = None
            self.globals = {}
            self.description = method.__doc__

        def __call__(self, message=None, **kwargs):
            if message.text == back_button:
                # if hasattr(self._previous, '_previous') and not self._previous._previous:
                #     # 2-steps back - return to MAIN
                #     return self.main_menu(message)
                if not self._previous:
                    return self.main_menu(message)

                if self._previous.markup:
                    self.bot.send_message(message.chat.id, self._previous.description, reply_markup=self._previous.markup)
                self.bot.register_next_step_handler_by_chat_id(message.chat.id, self._previous, **kwargs)
                return

            if message.text == main_menu_button:
                return self.main_menu(message)

            # 2-nd time submited text\markup
            # if self.markup and self.description:
            #     self.bot.send_message(message.chat.id, self.description, reply_markup=self.markup)

            try:
                # global values need to be redifined
                kwargs = {**kwargs, **self.globals}
                kwargs = self.method(self.bot, message, **kwargs)
            except Retry as r:
                print('Retry was raised in "{0}"'.format(self.description))
                self.bot.send_message(message.chat.id, str(r), reply_markup=self.markup)
                self.bot.register_next_step_handler_by_chat_id(message.chat.id, self, **kwargs)
                return

            if not self._next:
                # print('NO NEXT HANDLER')
                # self.bot.send_message(message.chat.id, 'Спасибо!', reply_markup=types.ReplyKeyboardRemove(selective=False))
                # self.bot.register_next_step_handler_by_chat_id(message.chat.id, self.main_menu)
                # return
                return self.main_menu(message)

            if self._next.markup:
                if isinstance(self._next.markup, DynamicMarkup):
                    self._next.markup = kwargs.get('next_step_markup')
                    del kwargs['next_step_markup']
                self.bot.send_message(message.chat.id, self._next.description, reply_markup=self._next.markup)
            else:
                self.bot.send_message(message.chat.id, 'Ашипка', reply_markup=types.ReplyKeyboardRemove(selective=False))
            self.bot.register_next_step_handler_by_chat_id(message.chat.id, self._next, **kwargs)

        def set_bot(self, bot):
            self.bot = bot

        def set_next(self, handler):
            self._next = handler

        def set_previous(self, handler):
            self._previous = handler

        def set_menu(self, handler):
            self.main_menu = handler

        def set_markup(self, markup):
            self.markup = markup

        def set_globals(self, globals):
            self.globals.update(globals)

    return wrapper(method)

from types import FunctionType

class Dialog:

    def __init__(self, handlers=None , main=None, globals=None):
        """

        :param init_handler: @function
        :param markup:
        :param main_handler:
        """
        self.main = None
        self._chain = []
        self.bot = None
        if handlers:
            for h in handlers:
                self.add_step(h)
        if main:
            self.set_main_handler(main)

        self.globals= globals or {}

    def set_main_handler(self, handler: FunctionType):
        self.main = handler
        for step in self._chain:
            step.set_menu(handler)

    def add_step(self, step_handler: FunctionType, markup=None):
        decorated = decor(step_handler)
        if self.globals:
            decorated.set_globals(self.globals)
        if self.main is not None:
            decorated.set_menu(self.main)

        if len(self._chain) > 0:
            decorated.set_previous(self._chain[-1])

        decorated.set_markup(markup)
        self._chain.append(decorated)

        if len(self._chain) > 1:
            self._chain[-2].set_next(self._chain[-1])

    def register_in_bot(self, bot):
        self.bot = bot
        for step in self._chain:
            step.set_bot(bot)

    # @property
    # def chain(self):
    #     return self._chain[0]

    def start(self, message):
        self.bot.send_message(message.chat.id, self._chain[0].description, reply_markup=self._chain[0].markup)
        self.bot.register_next_step_handler_by_chat_id(message.chat.id, self._chain[0])


class DynamicMarkup:
    pass

#
# def handle_init(message):
#     d = Dialog()
#     d.set_main_handler(handle_main_menu)
#     d.add_step(test1_handle)
#     d.add_step(test2_handle, gen_list_markup([1, 2, 3]))
#     d.add_step(test3_handle, DynamicMarkup())
#     d.add_step(test4_handle, gen_list_markup(['Сохранить', 'Отменить']))
#     d.register_in_bot(bot)
#     return d.chain(message)

