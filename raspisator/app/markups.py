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
    markup.row(types.KeyboardButton(main_menu_button))
    return markup


def gen_main_menu_markup():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    row = []
    row.append(types.KeyboardButton(main_menu['nearest']))
    row.append(types.KeyboardButton(main_menu['week']))
    row.append(types.KeyboardButton(main_menu['cal']))
    markup.row(*row)

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
    if not isinstance(subs, (list, tuple)):
        subs = [subs]
    markup = types.InlineKeyboardMarkup(row_width=1)
    # First row - Month and Year
    row = []
    row.append(types.InlineKeyboardButton('Ваши группы:', callback_data="settings-ignore"))
    for gr in subs:
        row.append(types.InlineKeyboardButton(gr['name'], callback_data='settings-subscription-' + str(gr['_id'])))
    row.append(types.InlineKeyboardButton('Закрыть', callback_data="dialog-close"))
    markup.add(*row)
    return markup

def gen_groups_choice_markup(subs, back_to=None, cached=None):
    markup = types.InlineKeyboardMarkup(row_width=1)
    row = []
    for gr, set in subs:
        if cached:
            if str(gr['_id']) == cached:
                name = emoj(':white_check_mark: {0}'.format(gr['name']))
            else:
                name = emoj(':white_medium_square: {0}'.format(gr['name']))
        else:
            if set['default']:
                name = emoj(':white_check_mark: {0}'.format(gr['name']))
            else:
                name = emoj(':white_medium_square: {0}'.format(gr['name']))

        row.append(types.InlineKeyboardButton(name,
                                              callback_data='change_group-select-{0}-{1}'.format(str(gr['_id']), back_to)))
    row.append(types.InlineKeyboardButton(emoj(":arrow_backward: Назад"), callback_data=str(back_to)))
    markup.add(*row)
    return markup


def gen_groups_settings_info():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    markup.row(types.KeyboardButton(groups_menu['groupset']))
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

    row.append(types.InlineKeyboardButton(emoj(':white_check_mark: По-умолчанию') if sub_state['default']
                                          else emoj(':white_medium_square: По-умолчанию'),
                                          callback_data='settings-groupdefault-'+sub_id))

    row.append(types.InlineKeyboardButton(emoj(":x: В разработке :x:"),
                                          callback_data='settings-back'))

    markup.row(*row)

    markup.row(types.InlineKeyboardButton(emoj(":arrow_backward: Назад"),
                                          callback_data='settings-back'))

    return markup


def create_calendar_inline(year, month, current_group=None):
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
    row.append(types.InlineKeyboardButton(emoj(":arrow_backward:"), callback_data="calendar-previous"))
    row.append(types.InlineKeyboardButton("Закрыть",callback_data="dialog-close"))
    row.append(types.InlineKeyboardButton(
            current_group, callback_data="change_group-init-calendar-current"
    ))
    row.append(types.InlineKeyboardButton(emoj(":arrow_forward:"), callback_data="calendar-next"))
    markup.row(*row)
    return markup

def create_month_back_inline(date):
    markup = types.InlineKeyboardMarkup()
    row = []
    row.append(types.InlineKeyboardButton(emoj(":arrow_backward:"), callback_data="calendar-current"))
    row.append(types.InlineKeyboardButton(date.strftime("%A, %d %B %Y"), callback_data="ignore"))
    row.append(types.InlineKeyboardButton("Закрыть",callback_data="dialog-close"))
    markup.row(*row)
    return markup


def create_week_inline(date, current_group=None):
    current_group = current_group or ''
    markup = types.InlineKeyboardMarkup()
    week = list(full_week(date))

    row=[]
    for day in week:
        row.append(types.InlineKeyboardButton(day.strftime("%a"), callback_data="week-day-" + day.strftime("%Y.%m.%d")))
    markup.row(*row)

    row = []
    row.append(types.InlineKeyboardButton(
            '{0} {1}-{2}'.format(emoj(':date:'), week[0].strftime('%d %b'), week[-1].strftime('%d %b')),
                    callback_data="ignore")
    )
    row.append(types.InlineKeyboardButton(
            current_group, callback_data="change_group-init-week-current"
    ))
    markup.row(*row)
    row=[]
    row.append(types.InlineKeyboardButton(emoj(":arrow_backward:"), callback_data="week-previous"))
    row.append(types.InlineKeyboardButton("Закрыть",callback_data="dialog-close"))
    row.append(types.InlineKeyboardButton(emoj(":arrow_forward:"), callback_data="week-next"))
    markup.row(*row)

    return markup

# Allowing to import only functions, described in whis module
__all__ = [m[0] for m in inspect.getmembers(sys.modules[__name__], inspect.isfunction)
               if m[1].__module__ == inspect.getmodule(sys.modules[__name__]).__name__]
