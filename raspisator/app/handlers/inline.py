
import inspect
from datetime import datetime
from .core import HandleMiddleware

from ..markups import create_group_settings_markup, gen_groups_settings_markup, \
    create_week_inline, create_month_back_inline, create_calendar_inline
from ..templates import selected_group_message, lessons_template, ParseMode, Messages
from ..shared.timeworks import next_weekday, last_weekday, next_month, last_month

class InlineParser(HandleMiddleware):
    __prefix__ = None

    def _add_handlers(self):
        pass

    def __call__(self, call):
        if self.__prefix__ == None:
            raise ValueError('Wrnog prefix for inline parser')
        call.data = call.data[len(self.__prefix__) + 1:]
        for method in inspect.getmembers(self, predicate=inspect.ismethod):
            if not call.data:
                return
            if call.data.startswith(method[0]):
                print('CALLING METHOD', self.__prefix__+'-'+method[0])
                return method[1](call, *call.data[len(method[0]) + 1:].split('-'))

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

    def next(self, call, *args):
        saved_date = self.cache.get_user_week(call.from_user.id)
        if (saved_date is not None):
            next_w = next_weekday(saved_date, 0)
            self.cache.set_user_week(call.from_user.id, next_w)
            markup = create_week_inline(next_w)
            self.bot.edit_message_text(Messages.select_date, call.from_user.id, call.message.message_id,
                                  reply_markup=markup)
            self.bot.answer_callback_query(call.id, text="")

    def previous(self, call, *args):
        saved_date = self.cache.get_user_week(call.from_user.id)
        if (saved_date is not None):
            last_w = last_weekday(saved_date, 0)
            self.cache.set_user_week(call.from_user.id, last_w)
            markup = create_week_inline(last_w)
            self.bot.edit_message_text(Messages.select_date, call.from_user.id, call.message.message_id,
                                  reply_markup=markup)
            self.bot.answer_callback_query(call.id, text="")

    def day(self, call, *args):
        date = datetime.strptime(args[0], "%Y.%m.%d")
        saved_date = self.cache.get_user_week(call.from_user.id)
        msg = self._get_user_lessons_by_date(call.from_user.id, date)
        if call.message.text != msg:
            self.bot.edit_message_text(msg,
                                  call.from_user.id, call.message.message_id,
                                  reply_markup=create_week_inline(saved_date),
                                  parse_mode=ParseMode.MARKDOWN)
        self.bot.answer_callback_query(call.id, text="")


class CalendarDialog(InlineParser):
    __prefix__ = 'calendar'


    def back_to_calendar(self, call, *args):
        shown = self.cache.get_user_cal(call.from_user.id)
        self.bot.edit_message_text(Messages.select_date, call.from_user.id, call.message.message_id,
                              reply_markup=create_calendar_inline(*shown))
        self.bot.answer_callback_query(call.id, text="")

    def next(self, call, *args):
        saved_date = self.cache.get_user_cal(call.from_user.id)
        if (saved_date is not None):
            next_m = next_month(*saved_date)
            self.cache.set_user_cal(call.from_user.id, next_m)
            markup = create_calendar_inline(*next_m)
            self.bot.edit_message_text(Messages.select_date, call.from_user.id, call.message.message_id,
                                  reply_markup=markup)
            self.bot.answer_callback_query(call.id, text="")

    def previous(self, call, *args):
        saved_date = self.cache.get_user_cal(call.from_user.id)
        if (saved_date is not None):
            last_m = last_month(*saved_date)
            self.cache.set_user_cal(call.from_user.id, last_m)
            markup = create_calendar_inline(*last_m)
            self.bot.edit_message_text(Messages.select_date, call.from_user.id, call.message.message_id,
                                  reply_markup=markup)
            self.bot.answer_callback_query(call.id, text="")

    def day(self, call, *args):
        saved_date = self.cache.get_user_cal(call.from_user.id)
        if (saved_date is not None):
            day = args[0]
            date = datetime(int(saved_date[0]), int(saved_date[1]), int(day), 0, 0, 0)
            msg = self._get_user_lessons_by_date(call.from_user.id, date)
            if call.message.text != msg:
                self.bot.edit_message_text(msg,
                                  call.from_user.id, call.message.message_id,
                                  reply_markup=create_month_back_inline(date),
                                  parse_mode=ParseMode.MARKDOWN)
            self.bot.answer_callback_query(call.id, text="")


class InlineHandlers(HandleMiddleware):
    def __init__(self,  bot, usersmodel=None, studiesmodel=None, celery=None, cache=None, *, debug=False):
        self.context = (bot, usersmodel, studiesmodel, celery, cache)
        super().__init__(bot, usersmodel, studiesmodel, celery, cache, debug=debug)

    @staticmethod
    def alias_filter(cls):
        def fun(call):
            return call.data.startswith(cls.__prefix__)
        return fun

    def _add_handler(self, f, **kwargs):
        handler_dict = self.bot._build_handler_dict(f, func=self.alias_filter(f))
        self.bot.add_callback_query_handler(handler_dict)

    def _add_handlers(self):
        self._add_handler(DialogClose(*self.context))
        self._add_handler(SettingsInline(*self.context))
        self._add_handler(WeekSwithcer(*self.context))
        self._add_handler(CalendarDialog(*self.context))
