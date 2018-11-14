
import inspect
from datetime import datetime
from .core import HandleMiddleware

from ..markups import create_group_settings_markup, gen_groups_settings_markup, create_week_inline
from ..templates import selected_group_message, lessons_template, ParseMode, Messages
from ..shared.timeworks import next_weekday, last_weekday

class InlineParser(HandleMiddleware):
    __prefix__ = None

    def _add_handlers(self):
        pass

    def __call__(self, call):
        if self.__prefix__ == None:
            raise ValueError('Wrnog prefix for inline parser')
        call.data = call.data[len(self.__prefix__) + 1:]
        for method in inspect.getmembers(self, predicate=inspect.ismethod):
            if call.data.startswith(method[0]):
                return method[1](call, *call.data[len(method[0]) + 1:].split('-'))


class SettingsInline(InlineParser):
    __prefix__ = 'settings'

    def subscription(self, call, *args):
        sub_id = args[0]
        sub, info = self.u.get_user_subscription_settings(call.from_user.id, sub_id)
        markup = create_group_settings_markup(sub['name'], sub_id, info)
        self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=markup, text="Управление подпиской")

    def push(self, call, *args):
        sub_id = call.data[5:]
        sub, info = self.u.change_notification_state(call.from_user.id, sub_id)
        markup = create_group_settings_markup(sub['name'], sub_id, info)
        self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                   reply_markup=markup, text="Управление подпиской")

    def unsub(self, call, *args):
        self.u.delete_subscription(call.from_user.id, args[0])
        subs = self.u.get_subscriptions(tel_user=call.from_user.id)
        self.bot.answer_callback_query(call.id, text=Messages.removed_group())
        self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=gen_groups_settings_markup(subs), text=Messages.please_select_group)

    def groupinfo(self, call, *args):
        sub_id = args[0]
        sub, info = self.u.get_user_subscription_settings(call.from_user.id, sub_id)
        markup = create_group_settings_markup(sub['name'], str(sub['_id']), info)
        text = selected_group_message(sub)
        self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=markup, text=text, parse_mode=ParseMode.MARKDOWN)

    def groupdefault(self, call, *args):
        print("HEREIAM")
        sub_id = args[0]
        if self.u.get_user_default_group(call.from_user.id) == sub_id:
            self.bot.answer_callback_query(call.id, text=Messages.already_default_group)
            return
        else:
            self.u.set_user_default_group(call.from_user.id, sub_id)
            sub, info = self.u.get_user_subscription_settings(call.from_user.id, sub_id)
            markup = create_group_settings_markup(sub['name'], sub_id, info)
            self.bot.answer_callback_query(call.id, text=Messages.setted_default_group)
            self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=markup, text="Управление подпиской")

    def back(self, call, *args):
        subs = self.u.get_subscriptions(tel_user=call.from_user.id, )
        self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=gen_groups_settings_markup(subs), text=Messages.please_select_group)


class DialogClose(InlineParser):
    __prefix__ = 'dialog'

    def close(self, call, *args):
        self.bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)


class WeekSwithcer(InlineParser):
    __prefix__ = 'week'

    def _get_user_lessons_by_date(self, uid, date):
        lessons = []
        for sub in self.u.get_subscriptions(tel_user=uid):
            lessons.append(self.s.get_lessons_in_day(sub["id"], date))

        if all([lesson == [] for lesson in lessons]):
            return Messages.no_schedule_on_date

        for lesson in lessons:
            if lesson == []:
                continue
            return lessons_template(lesson)

    def next(self, call, *args):
        saved_date = current_shown_weeks.get(chat_id)
        if (saved_date is not None):
            next_w = next_weekday(saved_date, 0)
            current_shown_weeks[chat_id] = next_w
            markup = create_week_inline(next_w)
            self.bot.edit_message_text(Messages.select_date, call.from_user.id, call.message.message_id,
                                  reply_markup=markup)
            self.bot.answer_callback_query(call.id, text="")

    def previous(self, call, *args):
        saved_date = current_shown_weeks.get(chat_id)
        if (saved_date is not None):
            next_w = last_weekday(saved_date, 0)
            current_shown_weeks[chat_id] = next_w
            markup = create_week_inline(next_w)
            self.bot.edit_message_text(Messages.select_date, call.from_user.id, call.message.message_id,
                                  reply_markup=markup)
            self.bot.answer_callback_query(call.id, text="")

    def day(self, call, *args):
        date = datetime.strptime(args[0], "%Y-%m-%d")

        self.bot.edit_message_text(self._get_user_lessons_by_date(call.from_user.id, date),
                              call.from_user.id, call.message.message_id,
                              reply_markup=create_week_inline(current_shown_weeks[chat_id]),
                              parse_mode=ParseMode.MARKDOWN)
        self.bot.answer_callback_query(call.id, text="")


class InlineHandlers(HandleMiddleware):
    def __init__(self,  bot, usersmodel=None, studiesmodel=None, celery=None, *, debug=False):
        self.context = (bot, usersmodel, studiesmodel, celery)
        super().__init__(bot, usersmodel, studiesmodel, celery, debug=debug)

    @staticmethod
    def alias_filter(cls):
        def fun(call):
            return call.data.startswith(cls.__prefix__)
        return fun

    def _add_handler(self, f, **kwargs):
        handler_dict = self.bot._build_handler_dict(f, func=self.alias_filter(f))
        self.bot.add_callback_query_handler(handler_dict)

    def _add_handlers(self):
        self._add_handler(SettingsInline(*self.context))
        self._add_handler(DialogClose(*self.context))