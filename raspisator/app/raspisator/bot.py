import os
import locale
import telebot
import logging

from pymongo import MongoClient

from .model import Studiesdata, Userdata
from .dialogs import *
from .chains import DynamicMarkup, Dialog
from .worker import celery
from .templates import ParseMode

locale.setlocale(locale.LC_ALL, ('RU','UTF8'))

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG if os.environ.get('BOT_DEBUG', '0') == '1'
                        else logging.INFO) # Outputs debug messages to console.

BOT_TOKEN = os.environ.get('BOT_TOKEN', None)
MONGO_CONNECTION = os.environ.get('MONGO_CONNECTION', 'mongodb://localhost:27017/')
MONGO_DB = os.environ.get('MONGO_DB', 'raspisator')


bot = telebot.TeleBot(token=BOT_TOKEN, threaded=False)
telebot.logger.warning('Initalizing bot with token: {0}'.format("<SANTINIZED>" if BOT_TOKEN != None else "<EMPTY>"))

conn = MongoClient(MONGO_CONNECTION)
logger.warning("Database connected" if 'ok' in conn.server_info() and
                                     conn.server_info()['ok'] == 1.0 else "Database connection failed!")

db = conn.get_database(MONGO_DB)
studiesmodel = Studiesdata(db)
usersmodel = Userdata(db)

# TODO: migrate this to DB
current_shown_dates = {}
current_shown_weeks = {}

def send_lessons_by_date(date, uid, chat):
    lessons = []
    for sub in usersmodel.get_subsciptions(tel_user=uid):
        lessons.append(studiesmodel.get_lessons_in_day(sub["id"], date))

    if all([lesson == [] for lesson in lessons]):
        bot.send_message(chat, Messages.no_shedule_on_date)
        return

    for lesson in lessons:
        if lesson == []:
            continue
        msg = lessons_template(lesson)
        bot.send_message(chat, msg, parse_mode=ParseMode.MARKDOWN)

@bot.message_handler(commands=['start'])
def handle_init(message):
    _, subs = init_user(message)
    if subs:
        bot.send_message(message.chat.id, text='Привет! Проверь список своих подписок. Для изменения настроек используй /subs')
        return handle_subscribes(message)

    else:
        return handle_faculty_init(message)

def init_user(message):
    username =  message.from_user.username if message.from_user.username else message.from_user.first_name
    user = usersmodel.create_or_get_user(message.from_user.id, username)
    subs = usersmodel.get_subsciptions(db_user=user)
    return user, subs

@bot.message_handler(commands=['subs'])
def handle_subscribes(message):
    _, subs = init_user(message)
    if not subs:
        bot.send_message(message.chat.id, text='Извините, мы не нашли ни одной подписки для Вас!\n'
                                               'Добавьте группу с помощью комманды /add',
                         parse_mode=ParseMode.MARKDOWN)
        return

    text = ''
    for gr in subs:
        text += selected_group_message(gr, use_intro=False) + '\n'
    bot.send_message(message.chat.id, text=text,
                    parse_mode=ParseMode.MARKDOWN,
                     reply_markup=gen_groups_settings_info())


@bot.message_handler(commands=['main'])
def handle_main_menu(message):
    markup = gen_main_menu_markup()
    bot.send_message(message.chat.id, "Добро пожаловать!", reply_markup=markup)


@bot.message_handler(commands=['add'])
def handle_faculty_init(message):
    faculties = studiesmodel.get_faculties_names()

    if not faculties:
        bot.send_message(message.chat.id, Messages.faculties_unaviable)
        return

    d = Dialog(globals={'m':studiesmodel, 'u':usersmodel})
    d.set_main_handler(handle_main_menu)
    d.add_step(handle_facultie_group_selection, markup=gen_list_markup(faculties))
    d.add_step(handle_group_kind, markup=DynamicMarkup())
    d.add_step(handle_group_type, markup=DynamicMarkup())
    d.add_step(handle_group_level, markup=DynamicMarkup())
    d.add_step(handle_group, markup=DynamicMarkup())
    d.add_step(handle_group_commit, markup=gen_dict_markup(group_checkout_mapper))
    d.register_in_bot(bot)
    return d.start(message)


@bot.message_handler(commands=['rasp'])
def handle_rasp_search(message):
    bot.send_message(message.chat.id, 'Что необходимо сделать?',
                     reply_markup=gen_search_menu_markup(), parse_mode=ParseMode.MARKDOWN)


@bot.message_handler(commands=['nearest'])
def get_nearest_lessons(message):
    user, subs = init_user(message)
    if not subs:
        bot.send_message(message.chat.id, Messages.no_schedule, reply_markup=gen_main_menu_markup())
        return
    lessons = []
    for sub in subs:
        lessons.append(studiesmodel.get_nearest_lesson(sub['id']))

    if not all(lessons):
        bot.send_message(message.chat.id, Messages.no_schedule, reply_markup=gen_main_menu_markup())
        return
    for lesson in lessons:
        msg = lessons_template([lesson])
        bot.send_message(message.chat.id, msg, parse_mode=ParseMode.MARKDOWN, )


@bot.message_handler(commands=['renew'])
def renew_user_subscriptions(message):
    resp = celery.send_task('deferred.get_user_subscribtion', args=[message.from_user.id])
    # resp = get_user_subscribtion.delay(message.from_user.id)
    bot.send_message(message.chat.id, Messages.schedule_will_be_updated,
                     reply_markup=gen_main_menu_markup(), parse_mode=ParseMode.MARKDOWN)


@bot.message_handler(commands=['groupset'])
def group_settings_handler(message):
    _, subs = init_user(message)
    bot.send_message(message.chat.id, text='Настройки групп',
                     reply_markup=gen_groups_settings_markup(subs))


@bot.message_handler(commands=['cal'])
def calendar_search_handler(message):
    now = datetime.now() #Current date
    chat_id = message.chat.id
    date = (now.year,now.month)
    current_shown_dates[chat_id] = date #Saving the current date in a dict
    markup= create_calendar(now.year,now.month)
    bot.send_message(message.chat.id, Messages.select_date, reply_markup=markup)


@bot.message_handler(commands=['teacher'])
def teacher_search_handler(message):
    d = Dialog(globals={'m': studiesmodel, 'u': usersmodel})
    d.set_main_handler(handle_main_menu)
    d.add_step(handle_teacher_name)
    d.add_step(handle_teacher_selection, markup=DynamicMarkup())
    d.add_step(handle_teacher_date, markup=DynamicMarkup())
    d.register_in_bot(bot)
    return d.start(message)


@bot.message_handler(commands=['week'])
def week_select_handler(message):
    current_shown_weeks[message.chat.id] = datetime.now()
    week_markup = create_week(datetime.now())
    bot.send_message(message.chat.id, Messages.select_date, reply_markup=week_markup)

## INLINE QUERY HANDLE NEAREST PAIR

@bot.inline_handler(lambda query: query.query == '')
def query_text(inline_query):
    subs = usersmodel.get_subsciptions(tel_user=inline_query.from_user.id)
    lessons = [studiesmodel.get_nearest_lesson(sub['id']) for sub in subs]
    groups_inline = gen_inline_groups_markup(subs, lessons)
    bot.answer_inline_query(inline_query.id, groups_inline)



## INLINE COMMANDS HANDLERS

@bot.callback_query_handler(func=lambda call: call.data.startswith('settings-'))
def callback_settings(call):
    # if is bot chat
    if not call.message:
        return

    # Strip 'settings-' from callback
    call.data = call.data[9:]

    def get_sub(id_, sub_id):
        sub = usersmodel.get_subsciptions(tel_user=id_, sub_id=sub_id)
        if sub != []:
            sub = sub[0]
        return sub

    if call.data.startswith('subscription-'):
        sub_id = call.data[13:]
        sub, info = usersmodel.get_user_subscription_settings(call.from_user.id, sub_id)
        markup = create_group_settings_markup(sub['name'], sub_id, info['notify'])
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=markup, text="Управление подпиской")

    if call.data.startswith('push-'):
        sub_id = call.data[5:]
        sub, info = usersmodel.change_notification_state(call.from_user.id, sub_id)
        markup = create_group_settings_markup(sub['name'], sub_id, sub['notify'])
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=markup, text="Управление подпиской")

    if call.data.startswith('unsub-'):
        sub_id = call.data[6:]
        removed_group = usersmodel.delete_subscription(call.from_user.id, sub_id)
        subs =  usersmodel.get_subsciptions(tel_user=call.from_user.id)
        bot.send_message(call.message.chat.id, text='Группа {0} удалена из ваших подписок!'.format(removed_group),)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=gen_groups_settings_markup(subs), text="Пожалуйста, выберите группу")

    if call.data.startswith('groupinfo-'):
        sub_id = call.data[10:]
        subs = get_sub(call.from_user.id, sub_id)
        text = selected_group_message(subs)
        bot.send_message(call.message.chat.id, text=text, parse_mode=ParseMode.MARKDOWN)

    # if call.data.startswith('close'):
    #     bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)

    if call.data.startswith('back'):
        subs = usersmodel.get_subsciptions(tel_user=call.from_user.id,)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=gen_groups_settings_markup(subs), text="Пожалуйста, выберите группу")


@bot.callback_query_handler(func=lambda call: call.data == "dialog-close")
def close_dialog(call):
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)



@bot.callback_query_handler(func=lambda call: call.data.startswith('week-'))
def callback_week(call):
    # if is bot chat
    if not call.message:
        return
    # Strip 'week-' from callback
    call.data = call.data[5:]
    chat_id = call.message.chat.id

    if call.data == 'next-week':
        saved_date = current_shown_weeks.get(chat_id)
        if (saved_date is not None):
            next_w = next_weekday(saved_date, 0)
            current_shown_weeks[chat_id] = next_w
            markup = create_week(next_w)
            bot.edit_message_text(Messages.select_date, call.from_user.id, call.message.message_id,
                              reply_markup=markup)
            bot.answer_callback_query(call.id, text="")

    if call.data == 'previous-week':
        saved_date = current_shown_weeks.get(chat_id)
        if (saved_date is not None):
            next_w = last_weekday(saved_date, 0)
            current_shown_weeks[chat_id] = next_w
            markup = create_week(next_w)
            bot.edit_message_text(Messages.select_date, call.from_user.id, call.message.message_id,
                              reply_markup=markup)
            bot.answer_callback_query(call.id, text="")

    if call.data.startswith('day-'):
        call.data = call.data[4:]
        date = datetime.strptime(call.data, "%Y-%m-%d")
        send_lessons_by_date(date, call.from_user.id, call.message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('calendar-'))
def callback_calendar(call):
    # if is bot chat
    if not call.message:
        return

    # Strip 'calendar-' from callback
    call.data = call.data[9:]
    chat_id = call.message.chat.id

    if call.data == 'next-month':
        saved_date = current_shown_dates.get(chat_id)
        if (saved_date is not None):
            next_m = next_month(*saved_date)
            current_shown_dates[chat_id] = next_m
            markup = create_calendar(*next_m)
            bot.edit_message_text(Messages.select_date, call.from_user.id, call.message.message_id,
                                  reply_markup=markup)
            bot.answer_callback_query(call.id, text="")

    if call.data == 'previous-month':
        saved_date = current_shown_dates.get(chat_id)
        if (saved_date is not None):
            last_m = last_month(*saved_date)
            current_shown_dates[chat_id] = last_m
            markup = create_calendar(*last_m)
            bot.edit_message_text(Messages.select_date, call.from_user.id, call.message.message_id,
                                  reply_markup=markup)
            bot.answer_callback_query(call.id, text="")

    if call.data.startswith('day-'):
        saved_date = current_shown_dates.get(chat_id)
        if (saved_date is not None):
            day = call.data[4:]
            date = datetime(int(saved_date[0]), int(saved_date[1]), int(day), 0, 0, 0)
            send_lessons_by_date(date, call.from_user.id, call.message.chat.id)


## ALIASES FOR COMMANDS
@bot.message_handler(func= lambda message: message.text == main_menu_button)
def _(message):
    return handle_main_menu(message)

@bot.message_handler(func= lambda message: message.text == group_setting_button)
def _(message):
    return group_settings_handler(message)
    # return handle_main_menu(message)

@bot.message_handler(func= lambda message: message.text == main_menu['add'])
def _(message):
    return handle_faculty_init(message)

@bot.message_handler(func= lambda message: message.text == main_menu['renew'])
def _(message):
    return renew_user_subscriptions(message)

@bot.message_handler(func= lambda message: message.text == main_menu['subs'])
def _(message):
    return handle_subscribes(message)

@bot.message_handler(func= lambda message: message.text == main_menu['nearset'])
def _(message):
    return get_nearest_lessons(message)

@bot.message_handler(func= lambda message: message.text == main_menu['plan'])
def _(message):
    return handle_rasp_search(message)

@bot.message_handler(func= lambda message: message.text == search_menu['calendar'])
def _(message):
    return calendar_search_handler(message)

@bot.message_handler(func= lambda message: message.text == search_menu['teacher'])
def _(message):
    return teacher_search_handler(message)

@bot.message_handler(func= lambda message: message.text == main_menu['week'])
def _(message):
    return week_select_handler(message)


## SERVICE COMMANDS
@bot.message_handler(func= lambda message: message.text == 'update-database-schema')
def _(message):
    resp = celery.send_task('deferred.get_groups_schema')
    bot.send_message(message.chat.id, 'Schema will be updated! Task: "{0}"'.format(str(resp)))

@bot.message_handler(func= lambda message: message.text == 'purge-unused-subs')
def _(message):
    resp = celery.send_task('deferred.unlink_non_used_subs')
    bot.send_message(message.chat.id, 'Unused subs will be removed! Task: "{0}"'.format(str(resp)))