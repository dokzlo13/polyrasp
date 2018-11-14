
import inspect
from datetime import datetime

from .core import HandleMiddleware
from ..markups import gen_main_menu_markup, gen_groups_settings_info, gen_list_markup, gen_dict_markup,\
    gen_search_menu_markup, gen_groups_settings_markup, create_week_inline, create_calendar_inline

from ..templates import Messages, ParseMode, selected_group_message, group_checkout_mapper, lessons_template

from ..chains import Dialog, StaticMarkup, DynamicMarkup

# DIALOGS
from ..dialogs import handle_facultie_group_selection, handle_group_kind, handle_group_type, \
    handle_group_level, handle_group, handle_group_commit
from ..dialogs import handle_teacher_name, handle_teacher_selection, handle_teacher_date

current_shown_weeks = {}

class CommandHandlers(HandleMiddleware):

    def _add_handler(self, f, **kwargs):
        handler_dict = self.bot._build_handler_dict(f, **kwargs)
        self.bot.add_message_handler(handler_dict)

    def _add_handlers(self):
        for method in inspect.getmembers(self, predicate=inspect.ismethod):
            if method[0].startswith('_'):
                continue
            # print('METHOD', method)
            self._add_handler(method[1], commands=[method[0].replace('_handler', '')],
                              content_types=['text'],
                              )

    def _init_user(self, message):
        username = message.from_user.username if message.from_user.username else message.from_user.first_name
        user = self.u.create_or_get_user(message.from_user.id, username)
        subs = self.u.get_subscriptions(db_user=user)
        return user, subs

    def start_handler(self, message):
        _, subs = self._init_user(message)
        if subs:
            self.bot.send_message(message.chat.id, text=Messages.hello)
            return self.subs_handler(message)

        else:
            return self.add_handler(message)

    def subs_handler(self, message):
        _, subs = self._init_user(message)
        if not subs:
            self.bot.send_message(message.chat.id, Messages.no_schedule,
                             parse_mode=ParseMode.MARKDOWN)
            return
        text = ''
        for gr in subs:
            text += selected_group_message(gr, use_intro=False) + '\n'
        self.bot.send_message(message.chat.id, text=text,
                         parse_mode=ParseMode.MARKDOWN,
                         reply_markup=gen_groups_settings_info())

    def add_handler(self, message):
        faculties = self.s.get_faculties_names()

        if not faculties:
            self.bot.send_message(message.chat.id, Messages.faculties_unaviable)
            self.broker.send_task('deferred.get_groups_schema')
            return

        d = Dialog(globals={'m': self.s, 'u': self.u})
        d.set_main_handler(self.main_handler)
        d.add_step(handle_facultie_group_selection, markup=StaticMarkup(gen_list_markup(faculties)))
        d.add_step(handle_group_kind, markup=DynamicMarkup())
        d.add_step(handle_group_type, markup=DynamicMarkup())
        d.add_step(handle_group_level, markup=DynamicMarkup())
        d.add_step(handle_group, markup=DynamicMarkup())
        d.add_step(handle_group_commit, markup=StaticMarkup(gen_dict_markup(group_checkout_mapper)))
        d.register_in_bot(self.bot)
        return d.start(message)

    def main_handler(self, message):
        markup = gen_main_menu_markup()
        self.bot.send_message(message.chat.id, Messages.welcome, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

    def plan_handler(self, message):
        self.bot.send_message(message.chat.id, Messages.what_to_do,
                         reply_markup=gen_search_menu_markup(), parse_mode=ParseMode.MARKDOWN)

    def nearest_handler(self, message):
        user, subs = self._init_user(message)
        if not subs:
            self.bot.send_message(message.chat.id, Messages.no_schedule, reply_markup=gen_main_menu_markup())
            return
        lessons = []
        for sub in subs:
            lessons.append(self.s.get_nearest_lesson(sub['id']))

        if not all(lessons):
            self.bot.send_message(message.chat.id, Messages.no_schedule, reply_markup=gen_main_menu_markup())
            return
        for lesson in lessons:
            msg = lessons_template([lesson])
            self.bot.send_message(message.chat.id, msg, parse_mode=ParseMode.MARKDOWN, )

    def renew_handler(self, message):
        resp = self.broker.send_task('deferred.get_user_subscribtion', args=[message.from_user.id])
        # resp = get_user_subscribtion.delay(message.from_user.id)
        self.bot.send_message(message.chat.id, Messages.schedule_will_be_updated,
                         reply_markup=gen_main_menu_markup(), parse_mode=ParseMode.MARKDOWN)

    def groupset_handler(self, message):
        _, subs = self._init_user(message)
        self.bot.send_message(message.chat.id, text=Messages.settings,
                         reply_markup=gen_groups_settings_markup(subs))

    def cal_handler(self, message):
        now = datetime.now()  # Current date
        date = (now.year, now.month)
        self.cache.set_user_cal(message.from_user.id, date)
        default_group = self.u.get_user_default_group(message.from_user.id)
        self.cache.set_user_curr_gr(message.from_user.id, default_group)
        sub, _ = self.u.get_user_subscription_settings(
                message.from_user.id,
                default_group
        )
        markup = create_calendar_inline(now.year, now.month, sub['name'])
        self.bot.send_message(message.chat.id, Messages.select_date, reply_markup=markup)

    def teacher_handler(self, message):
        d = Dialog(globals={'m': self.s, 'u': self.u})
        d.set_main_handler(self.main_handler)
        d.add_step(handle_teacher_name)
        d.add_step(handle_teacher_selection, markup=DynamicMarkup())
        d.add_step(handle_teacher_date, markup=DynamicMarkup())
        d.register_in_bot(self.bot)
        return d.start(message)

    def week_handler(self, message):
        self.cache.set_user_week(message.from_user.id, datetime.now())
        default_group = self.u.get_user_default_group(message.from_user.id)
        self.cache.set_user_curr_gr(message.from_user.id, default_group)
        sub, _ = self.u.get_user_subscription_settings(
                message.from_user.id,
                default_group
        )
        week_markup = create_week_inline(datetime.now(), sub['name'])
        self.bot.send_message(message.chat.id, Messages.select_date, reply_markup=week_markup)
