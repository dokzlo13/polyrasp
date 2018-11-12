import inspect
import sys
import calendar

from telebot import types
from .templates import main_menu, emoj, main_menu_button, back_button, search_menu, groups_menu
from .templates import lessons_template, short_group
from .shared.timeworks import full_week

def gen_dict_markup(mapper, back=True):
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for facult in mapper.keys():
        markup.add(facult)
    markup.add(main_menu_button)
    if back:
        markup.add(back_button)
    return markup


def gen_list_markup(list_, key=None, back=True):
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for item in list_:
        if key:
            markup.add(str(item[key]))
        else:
            markup.add(str(item))

    markup.add(main_menu_button)
    if back:
        markup.add(back_button)
    return markup


def gen_search_menu_markup():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(types.KeyboardButton(search_menu['teacher']))
    markup.row(types.KeyboardButton(search_menu['calendar']))
    markup.row(types.KeyboardButton(main_menu_button))
    return markup


def gen_main_menu_markup():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(types.KeyboardButton(main_menu['nearset']), types.KeyboardButton(main_menu['week']))
    row = []
    row.append(types.KeyboardButton(main_menu['plan']))
    row.append(types.KeyboardButton(main_menu['subs']))
    row.append(types.KeyboardButton(main_menu['renew']))
    markup.row(*row)
    return markup

def gen_inline_groups_markup(subs, lessons):
    groups_inline = []
    for sub, lesson in zip(subs, lessons):
        if lesson:
            msg = lessons_template([lesson], markup=False)
        else:
            msg = 'Нет информации о ближайшей паре'
        r = types.InlineQueryResultArticle(str(sub['_id']), short_group(sub),
                                           types.InputTextMessageContent(msg))
        groups_inline.append(r)
    return groups_inline


def gen_groups_settings_markup(subs):
    markup = types.InlineKeyboardMarkup(row_width=1)
    # First row - Month and Year
    row = []
    row.append(types.InlineKeyboardButton('Ваши группы:', callback_data="settings-ignore"))
    for gr in subs:
        row.append(types.InlineKeyboardButton(gr['name'], callback_data='settings-subscription-' + str(gr['_id'])))
    row.append(types.InlineKeyboardButton('Закрыть', callback_data="dialog-close"))
    markup.add(*row)
    return markup

#
# def gen_groups_choice_markup(subs):
#     markup = types.InlineKeyboardMarkup(row_width=1)
#     # First row - Month and Year
#     row = []
#     row.append(types.InlineKeyboardButton('Ваши группы:', callback_data="ignore"))
#     for gr in subs:
#         row.append(types.InlineKeyboardButton(gr['name'], callback_data='calendar-select-group-' + str(gr['_id'])))
#     row.append(types.InlineKeyboardButton('Закрыть', callback_data="dialog-close"))
#     markup.add(*row)
#     return markup


def gen_groups_settings_info():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    markup.row(types.KeyboardButton(groups_menu['settings']))
    markup.row(types.KeyboardButton(groups_menu['add']))
    markup.row(types.KeyboardButton(main_menu_button))
    return markup


def create_group_settings_markup(name, sub_id, sub_state):
    markup = types.InlineKeyboardMarkup(row_width=2)
    row = []
    row.append(types.InlineKeyboardButton(emoj(':no_entry_sign: Удалить'),
                               callback_data='settings-unsub-' + sub_id))
    row.append(types.InlineKeyboardButton(emoj(':information_source: ' + name),
                                          callback_data="settings-groupinfo-"+sub_id))
    markup.row(*row)

    row = []

    # row.append(types.InlineKeyboardButton(emoj(':no_bell: Не уведомлять') \
    #                                           if sub_state else \
    #                                           emoj(':bell: Уведомлять'),
    #                                       callback_data='settings-push-'+sub_id))

    row.append(types.InlineKeyboardButton(emoj(":x: В разработке :x:"),
                                          callback_data='settings-back'))

    # row.append(types.InlineKeyboardButton(emoj(':alarm_clock: Время уведомлений'),
    #                                       callback_data='settings-time-'+sub_id))

    row.append(types.InlineKeyboardButton(emoj(":x: В разработке :x:"),
                                          callback_data='settings-back'))

    markup.row(*row)

    markup.row(types.InlineKeyboardButton(emoj(":arrow_backward: Назад"),
                                          callback_data='settings-back'))

    return markup


def create_calendar(year,month):
    markup = types.InlineKeyboardMarkup()
    #First row - Month and Year
    row=[]
    row.append(types.InlineKeyboardButton(calendar.month_name[month]+" "+str(year),callback_data="ignore"))
    markup.row(*row)
    #Second row - Week Days
    week_days=["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    row=[]
    for day in week_days:
        row.append(types.InlineKeyboardButton(day,callback_data="ignore"))
    markup.row(*row)

    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row=[]
        for day in week:
            if(day==0):
                row.append(types.InlineKeyboardButton(" ",callback_data="ignore"))
            else:
                row.append(types.InlineKeyboardButton(str(day),callback_data="calendar-day-"+str(day)))
        markup.row(*row)
    #Last row - Buttons
    row=[]
    row.append(types.InlineKeyboardButton(emoj(":arrow_backward:"), callback_data="calendar-previous-month"))
    row.append(types.InlineKeyboardButton("Закрыть",callback_data="dialog-close"))
    row.append(types.InlineKeyboardButton(emoj(":arrow_forward:"), callback_data="calendar-next-month"))
    markup.row(*row)
    return markup


def create_week(date):
    markup = types.InlineKeyboardMarkup()
    week = list(full_week(date))

    row=[]
    for day in week:
        row.append(types.InlineKeyboardButton(day.strftime("%a"), callback_data="week-day-" + day.strftime("%Y-%m-%d")))
    markup.row(*row)

    row=[]
    for day in week:
        row.append(types.InlineKeyboardButton(day.strftime("%d"), callback_data="week-day-" + day.strftime("%Y-%m-%d")))
    markup.row(*row)

    markup.row(types.InlineKeyboardButton(emoj(':date:')+ week[0].strftime(' %B').capitalize(), callback_data="ignore"))

    row=[]
    row.append(types.InlineKeyboardButton(emoj(":arrow_backward:"), callback_data="week-previous-week"))
    row.append(types.InlineKeyboardButton("Закрыть",callback_data="dialog-close"))
    row.append(types.InlineKeyboardButton(emoj(":arrow_forward:"), callback_data="week-next-week"))
    markup.row(*row)

    return markup

# Allowing to import only functions, described in whis module
__all__ = [m[0] for m in inspect.getmembers(sys.modules[__name__], inspect.isfunction)
               if m[1].__module__ == inspect.getmodule(sys.modules[__name__]).__name__]
