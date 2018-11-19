
import inspect
from datetime import datetime
from .core import HandleMiddleware

from ..markups import create_group_settings_markup, gen_groups_settings_markup, \
    create_week_inline, create_month_back_inline, create_calendar_inline, \
    gen_groups_choice_markup

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
            if method[0].startswith('_'):
                continue
            if not call.data:
                return
            if call.data.startswith(method[0]):
                args = call.data[len(method[0]) + 1:].split('-')
                # print('User "{0}" call inline "{1}" args={2}'.format(call.from_user.id, self.__prefix__+'-'+method[0], args))
                return method[1](call, *args)

    def _get_user_lessons_by_date(self, uid, date, markup=True):
        lessons = []
        sub_id = self.cache.get_user_curr_gr(uid)
        for sub in self.u.get_subscriptions(tel_user=uid, sub_id=sub_id):
            lessons.append(self.s.get_lessons_in_day(sub["id"], date))

        if all([lesson == [] for lesson in lessons]):
            return Messages.no_schedule_on_date

        for lesson in lessons:
            if lesson == []:
                continue
            return lessons_template(lesson, markup)

    def same_message(self, remote, uid, date):
        local = self._get_user_lessons_by_date(uid, date, markup=False)
        return  local.split() == remote.split()

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
        subs = list(self.u.get_subscriptions(tel_user=call.from_user.id))
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
        subs = list(self.u.get_subscriptions(tel_user=call.from_user.id, ))
        self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=gen_groups_settings_markup(subs), text=Messages.please_select_group)


class DialogClose(InlineParser):
    __prefix__ = 'dialog'

    def close(self, call, *args):
        self.bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)


class WeekSwithcer(InlineParser):
    __prefix__ = 'week'

    def _create_week_inline(self, uid, date):
        gr = self.cache.get_user_curr_gr(uid)
        sub, _ = self.u.get_user_subscription_settings(uid, gr)
        week_markup = create_week_inline(date, sub['name'])
        return week_markup

    def respond_mock(self, call, markup):
        # if call.message.text != Messages.select_date:
        self.bot.edit_message_text(Messages.select_date, call.from_user.id, call.message.message_id,
                                   reply_markup=markup)
        self.bot.answer_callback_query(call.id, text="")

    def current(self, call, *args):
        saved_date = self.cache.get_user_week(call.from_user.id)
        markup = self._create_week_inline(call.from_user.id, saved_date)
        self.respond_mock(call, markup)

    def next(self, call, *args):
        saved_date = self.cache.get_user_week(call.from_user.id)
        if (saved_date is not None):
            next_w = next_weekday(saved_date, 0)
            self.cache.set_user_week(call.from_user.id, next_w)
            markup = self._create_week_inline(call.from_user.id, next_w)
            self.respond_mock(call, markup)

    def previous(self, call, *args):
        saved_date = self.cache.get_user_week(call.from_user.id)
        if (saved_date is not None):
            last_w = last_weekday(saved_date, 0)
            self.cache.set_user_week(call.from_user.id, last_w)
            markup = self._create_week_inline(call.from_user.id, last_w)
            self.respond_mock(call, markup)

    def day(self, call, *args):
        uid = call.from_user.id
        date = datetime.strptime(args[0], "%Y.%m.%d")
        saved_date = self.cache.get_user_week(uid)
        if not self.same_message(call.message.text, uid, date):
            self.bot.edit_message_text(self._get_user_lessons_by_date(uid, date),
                                  uid, call.message.message_id,
                                  reply_markup=self._create_week_inline(uid, saved_date),
                                  parse_mode=ParseMode.MARKDOWN,
                                  )
        self.bot.answer_callback_query(call.id, text="")


class CalendarDialog(InlineParser):
    __prefix__ = 'calendar'

    def _create_calendar_inline(self, uid, shown):
        gr = self.cache.get_user_curr_gr(uid)
        sub, _ = self.u.get_user_subscription_settings(uid, gr)
        cal_markup = create_calendar_inline(*shown, sub['name'])
        return cal_markup

    def current(self, call, *args):
        shown = self.cache.get_user_cal(call.from_user.id)
        markup = self._create_calendar_inline(call.from_user.id, shown)
        self.respond_mock(call, markup)

    def respond_mock(self, call, markup):
        # if call.message.text != Messages.select_date:
        self.bot.edit_message_text(Messages.select_date, call.from_user.id, call.message.message_id,
                                   reply_markup=markup)
        self.bot.answer_callback_query(call.id, text="")

    def next(self, call, *args):
        saved_date = self.cache.get_user_cal(call.from_user.id)
        if (saved_date is not None):
            next_m = next_month(*saved_date)
            self.cache.set_user_cal(call.from_user.id, next_m)
            markup = self._create_calendar_inline(call.from_user.id, next_m)
            self.respond_mock(call, markup)

    def previous(self, call, *args):
        saved_date = self.cache.get_user_cal(call.from_user.id)
        if (saved_date is not None):
            last_m = last_month(*saved_date)
            self.cache.set_user_cal(call.from_user.id, last_m)
            markup = self._create_calendar_inline(call.from_user.id, last_m)
            self.respond_mock(call, markup)

    def day(self, call, *args):
        saved_date = self.cache.get_user_cal(call.from_user.id)
        if (saved_date is not None):
            uid = call.from_user.id
            day = args[0]
            date = datetime(int(saved_date[0]), int(saved_date[1]), int(day), 0, 0, 0)
            if not self.same_message(call.message.text, uid, date):
                self.bot.edit_message_text(self._get_user_lessons_by_date(uid, date),
                                  uid, call.message.message_id,
                                  reply_markup=create_month_back_inline(date),
                                  parse_mode=ParseMode.MARKDOWN)
            self.bot.answer_callback_query(call.id, text="")


class CurrrentGroupSwitcher(InlineParser):
    __prefix__ = 'change_group'

    def _create_changegroup_markup(self, uid, *back_to):
        back_to = '-'.join(back_to)
        subs = self.u.get_user_subscription_settings(uid)
        cached = self.cache.get_user_curr_gr(uid)
        markup = gen_groups_choice_markup(subs, back_to, cached)
        return markup

    def _respond_mock(self, call, markup):
        self.bot.edit_message_text(Messages.please_select_current_group, call.from_user.id, call.message.message_id,
                                   reply_markup=markup)
        self.bot.answer_callback_query(call.id, text="")

    def init(self, call, *args):
        self._respond_mock(call, self._create_changegroup_markup(call.from_user.id, *args))

    def select(self, call, *args):
        to_select = args[0]
        curr = self.cache.get_user_curr_gr(call.from_user.id)
        if curr == to_select:
            self.bot.answer_callback_query(call.id, text=Messages.already_current_group)
            return

        self.cache.set_user_curr_gr(call.from_user.id, to_select)
        self.bot.answer_callback_query(call.id, text=Messages.group_select_succeed)
        self._respond_mock(call, self._create_changegroup_markup(call.from_user.id, *args[1:]))


class InlineHandlers(HandleMiddleware):
    def __init__(self,  bot, usersmodel=None, studiesmodel=None, celery=None, cache=None, *, debug=False):
        self.context = (bot, usersmodel, studiesmodel, celery, cache)
        super().__init__(bot, usersmodel, studiesmodel, celery, cache, debug=debug)

    @staticmethod
    def alias_filter(cls):
        def fun(call):
            return call.data.startswith(cls.__prefix__)
        return fun

    def _add_handler(self, parser, **kwargs):
        handler_dict = self.bot._build_handler_dict(parser(*self.context), func=self.alias_filter(parser))
        self.bot.add_callback_query_handler(handler_dict)

    def _add_handlers(self):
        self._add_handler(DialogClose)
        self._add_handler(SettingsInline)
        self._add_handler(WeekSwithcer)
        self._add_handler(CalendarDialog)
        self._add_handler(CurrrentGroupSwitcher)
