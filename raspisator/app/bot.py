import os
import locale
import telebot
import logging

from pymongo import MongoClient

from .shared.model import Studiesdata, Userdata
from .shared.timeworks import next_month, last_month

from .worker import celery
from .templates import ParseMode, Messages, main_menu, groups_menu, search_menu, main_menu_button
from .handlers import CommandHandlers, CommandsAliases, InlineHandlers

locale.setlocale(locale.LC_ALL, ('RU','UTF8'))

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG if os.environ.get('BOT_DEBUG', '0') == '1'
                        else logging.INFO) # Outputs debug messages to console.

BOT_TOKEN = os.environ.get('BOT_TOKEN', None)
MONGO_CONNECTION = os.environ.get('MONGO_CONNECTION', 'mongodb://localhost:27017/')
MONGO_DB = os.environ.get('MONGO_DB', 'raspisator')


# bot = telebot.TeleBot(token=BOT_TOKEN, threaded=False)
bot = telebot.AsyncTeleBot(token=BOT_TOKEN, threaded=False)
telebot.logger.warning('Initalizing bot with token: {0}'.format("<SANTINIZED>" if BOT_TOKEN != None else "<EMPTY>"))

conn = MongoClient(MONGO_CONNECTION)
logger.warning("Database connected" if 'ok' in conn.server_info() and
                                     conn.server_info()['ok'] == 1.0 else "Database connection failed!")

db = conn.get_database(MONGO_DB)
studiesmodel = Studiesdata(db)
usersmodel = Userdata(db)


handlers = CommandHandlers(bot, usersmodel=usersmodel, studiesmodel=studiesmodel, celery=celery)
CommandsAliases(handlers, search_menu, main_menu, groups_menu, {'main': main_menu_button})
InlineHandlers(bot, usersmodel=usersmodel, studiesmodel=studiesmodel, celery=celery)

## INLINE QUERY HANDLE NEAREST PAIR

@bot.inline_handler(lambda query: query.query == '')
def query_text(inline_query):
    subs = usersmodel.get_subscriptions(tel_user=inline_query.from_user.id)
    lessons = [studiesmodel.get_nearest_lesson(sub['id']) for sub in subs]
    groups_inline = gen_inline_groups_markup(subs, lessons)
    bot.answer_inline_query(inline_query.id, groups_inline)

# @bot.callback_query_handler(func=lambda call: call.data.startswith('change-group-'))
# def callback_chande(call):
#     call.data = call.data[13:]
#     if call.data.startswith('init-'):
#         call.data = call.data[5:]
#         markup = create_group_change_markup(groups_aviable, return_to=call.data)
#         bot.edit_message_text(Messages.select_group_to_show, call.from_user.id, call.message.message_id,
#                               reply_markup=markup)
#         bot.answer_callback_query(call.id, text="")
#     if call.data.startswith('select-'):
#         call.data = call.data[7:]
#         group_id, back_to = call.data[:24], call.data[25:]
#         usersmodel.set_user_current_group(call.from_user.id, group_id)
#         # CHECK HERE WHERE TO BACK
#         # TODO: Create callbacks commands parser

## SERVICE COMMANDS
@bot.message_handler(func= lambda message: message.text == 'update-database-schema')
def _(message):
    resp = celery.send_task('deferred.get_groups_schema')
    bot.send_message(message.chat.id, 'Schema will be updated! Task: "{0}"'.format(str(resp)))

@bot.message_handler(func= lambda message: message.text == 'purge-unused-subs')
def _(message):
    resp = celery.send_task('deferred.unlink_non_used_subs')
    bot.send_message(message.chat.id, 'Unused subs will be removed! Task: "{0}"'.format(str(resp)))

@bot.message_handler(func= lambda message: message.text == 'purge-timeouts')
def _(message):
    resp = celery.send_task('deferred.purge_subscription_timeouts')
    bot.send_message(message.chat.id, 'Timeouts purged! "{0}"'.format(str(resp)))