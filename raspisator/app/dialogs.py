import inspect
import sys
from datetime import datetime

from telebot import types

from .templates import ParseMode
from .templates import selected_group_message
from .templates import level_mapper, type_mapper, kind_mapper, group_checkout_mapper
from .markups import *
from .chains import Retry
from .shared.timeworks import convert_concat_day_and_lesson

from .worker import celery


def handle_facultie_group_selection(bot, message, **kwargs):
    "Выберите институт:"
    bot.send_chat_action(message.chat.id, 'typing')
    m = kwargs.get('m')
    facult = m.get_facultie_by_facultie_name(message.text)
    if not facult:
        raise Retry("В данном институте нет групп, выберите другой институт")
    # bot.send_message(message.chat.id, "Ищу группы для {0}".format(facult['abbr']),
    #                        reply_markup=types.ReplyKeyboardRemove())
    groups = m.get_groups_by(fac_id=facult['id'])

    if not groups:
        raise Retry("В данном институте нет групп, выберите другой институт")

    kwargs.update({'next_step_markup': gen_dict_markup(kind_mapper)})
    kwargs.update(dict(facult_id=facult['id']))
    return kwargs


def handle_group_kind(bot, message, **kwargs):
    "Выберите квалификацию:"
    m = kwargs.get('m')
    facult_id = kwargs.get('facult_id')
    kind = kind_mapper.get(message.text)
    groups = m.get_groups_by(fac_id=facult_id, kind=kind)
    if not groups:
        raise Retry('Нет групп с такой квалификацией!')

    kwargs.update({'next_step_markup': gen_dict_markup(type_mapper)})
    kwargs.update(dict(facult_id=facult_id, kind=kind))
    return kwargs


def handle_group_type(bot, message, **kwargs):
    "Выберите форму обучения:"
    facult_id = kwargs.get('facult_id')
    m = kwargs.get('m')
    kind = kwargs.get('kind')
    type_ = type_mapper.get(message.text)
    groups = m.get_groups_by(fac_id=facult_id, kind=kind, type_=type_)
    if not groups:
        raise Retry('Нет групп с такой формой обучения!')
    kwargs.update({'next_step_markup': gen_dict_markup(level_mapper)})
    kwargs.update(dict(facult_id=facult_id, kind=kind, type_=type_))
    return kwargs


def handle_group_level(bot, message, **kwargs):
    "Выберите курс:"
    m = kwargs.get('m')
    facult_id = kwargs.get('facult_id')
    kind = kwargs.get('kind')
    type_ = kwargs.get('type_')
    level = level_mapper.get(message.text)
    groups = m.get_groups_by(fac_id=facult_id, kind=kind,  type_=type_, level=level)
    if not groups:
        raise Retry("Нет групп для данного курса")
    kwargs.update({'next_step_markup': gen_list_markup(groups, 'name')})
    return kwargs


def handle_group(bot, message, **kwargs):
    "Выберите группу:"
    m = kwargs.get('m')
    group = m.get_group_by_name(message.text)
    if not group:
        raise Retry("Для данной группы нет расписания, выберите другую группу")

    facult = m.get_facult_by_react_id(group["facultie"])
    text = selected_group_message(group, facult)
    bot.send_message(message.chat.id, text=text, parse_mode=ParseMode.MARKDOWN)
    kwargs.update(dict(group=group))
    return kwargs


def handle_group_commit(bot, message, **kwargs):
    "Подвердите выбор:"

    u = kwargs.get('u')
    group = kwargs.get('group')
    confirm = group_checkout_mapper.get(message.text)
    if confirm:
        sub = u.add_subscription(message.from_user.id, group, message.chat.id)
        celery.send_task('deferred.get_subscribtion', args=[str(sub)])

        text = 'Ваша группа добавлена в список подписок!\nПросмотреть все подписки можно командой /subs' \
               '\n*Информация о расписании скоро появится!*'
        bot.send_message(message.chat.id, text=text, parse_mode=ParseMode.MARKDOWN,
                               reply_markup=types.ReplyKeyboardRemove(selective=False))


def handle_teacher_name(bot, message, **kwargs):
    "Введите имя преподавателя:"

    result = celery.send_task('deferred.get_teacher_search', args=[message.text])
    # result = get_teacher_search.delay(message.text)
    bot.send_message(message.chat.id, 'Произвожу поиск...')
    result = result.wait(timeout=10)
    if not result:
        raise Retry('Поиск не дал результатов! Введите другой запрос, или вернитесь в меню /main')

    kwargs.update({'next_step_markup': gen_list_markup(result, 'full_name')})
    kwargs.update({'teachers': result})
    return kwargs

def handle_teacher_selection(bot, message, **kwargs):
    "Выберите преподавателя из списка:"

    result =None
    teachers = kwargs.get('teachers')
    for teacher in teachers:
        if teacher['full_name'] == message.text:
            result = celery.send_task('deferred.get_teacher_lessons', args=[teacher['id']])
            # result = get_teacher_lessons.delay(teacher['id'])
            result = result.wait(timeout=10)

    if not result:
        raise Retry('Для этого преподавателя нет расписания!')

    kwargs.update({'next_step_markup': gen_list_markup(result, 'date')})
    kwargs.update({'teacher_rasp': result})
    return kwargs


def handle_teacher_date(bot, message, **kwargs):
    "Выберите необходимую дату:"

    teacher_rasp = kwargs.get('teacher_rasp')

    lessons = []

    for rasp in teacher_rasp:
        if rasp == []:
            continue
        weekday = datetime.strptime(rasp['date'], '%Y-%m-%d')
        if datetime.strptime(message.text, '%Y-%m-%d') == weekday:
            for lesson in rasp['lessons']:
                lesson['time_start'] = convert_concat_day_and_lesson(lesson['time_start'], weekday)
                lesson['time_end'] = convert_concat_day_and_lesson(lesson['time_end'], weekday)
                lesson['weekday'] = rasp['weekday']
                lessons.append(lesson)
    # use only lessons, without weeks info
    if not lessons:
        raise Retry('Нет расписания на этот день')

    result = lessons_template(lessons)
    bot.send_message(message.chat.id, result, parse_mode=ParseMode.MARKDOWN)
    return kwargs

# Allowing to import only functions, described in whis module
__all__ = [m[0] for m in inspect.getmembers(sys.modules[__name__], inspect.isfunction)
               if m[1].__module__ == inspect.getmodule(sys.modules[__name__]).__name__]
