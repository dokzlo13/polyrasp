import os
from celery import Celery, group
from celery.schedules import crontab
from datetime import datetime, timedelta
import locale


from .shared.model import context_model
from .shared.model import Studiesdata, Userdata
from .shared.timeworks import timeout_has_passed, get_weeks_range, convert_concat_day_and_lesson, strf_list
from .collection import collect_groups, collect_faculties, collect_rasp, get_teachers, get_teacher_rasp

locale.setlocale(locale.LC_ALL, ('RU','UTF8'))

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
MONGO_CONNECTION = os.environ.get('MONGO_CONNECTION', 'mongodb://localhost:27017/')
MONGO_DB = os.environ.get('MONGO_DB', 'raspisator')


UserStandalone = context_model(Userdata, MONGO_CONNECTION, MONGO_DB)
StudiesStandalone = context_model(Studiesdata, MONGO_CONNECTION, MONGO_DB)


app = Celery(broker=CELERY_BROKER_URL,
             backend=CELERY_RESULT_BACKEND,
             )


app.conf.timezone = 'UTC'

RENEW_TIMEOUT = 60 * 30
INITIAL_WEEKS_DEPTH = 10
WEEKS_DEPTH = 2
# NOTIFY_DELAY = 4
UNLINK_DELAY = 60.0*20

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(RENEW_TIMEOUT*2, get_all_subscibtions_data.s(), name='Collect all subscriptions data every hour')
    sender.add_periodic_task(UNLINK_DELAY, unlink_non_used_subs.s(), name='Remove unused subscriptions')
    # sender.add_periodic_task(30.0, test.s('world'), expires=10)
    # Executes every hour
    sender.add_periodic_task(
        crontab(hour=3),
        get_groups_schema.s(),
    )


def merge_dictionaries(dict1, dict2):
    merged_dictionary = {}

    for key in dict1:
        if key in dict2:
            new_value = dict1[key] + dict2[key]
        else:
            new_value = dict1[key]

        merged_dictionary[key] = new_value

    for key in dict2:
        if key not in merged_dictionary:
            merged_dictionary[key] = dict2[key]

    return merged_dictionary


@app.task(name='deferred.get_groups_schema')
def get_groups_schema():
    with StudiesStandalone(purge_schema=['faculties', 'groups']) as s:

        faculties_data = collect_faculties()
        s.update_faculties(faculties_data)

        groups_total = 0
        for facult in faculties_data:
            groups_data = collect_groups(facult['id'])
            if groups_data:
                for gr in groups_data:
                    groups_total += 1
                    gr.update({'facultie': facult['id']})
                s.update_groups(groups_data)
        return {'faculties': len(faculties_data), 'groups': groups_total}


def collect_lessons_data(facult, id_, params=None):
    current_rasp = collect_rasp(facult, id_, params=params)
    if current_rasp == None:
        return
    for rasp in current_rasp:
        if rasp == []:
            continue
        weekday = datetime.strptime(rasp['date'], '%Y-%m-%d')
        for lesson in rasp['lessons']:
            lesson['time_start'] = convert_concat_day_and_lesson(lesson['time_start'], weekday)
            lesson['time_end'] = convert_concat_day_and_lesson(lesson['time_end'], weekday)
            lesson['weekday'] = rasp['weekday']
    # use only lessons, without weeks info
    lessons = []
    for lesson in [rasp['lessons'] for rasp in current_rasp]:
        lessons.extend(lesson)
    return lessons


@app.task
def process_sub(sub, force=False, initial=False):
    updates = {'timeout_passed':False}
    with StudiesStandalone() as s, \
            UserStandalone() as u:
        if not force and not timeout_has_passed(sub, RENEW_TIMEOUT):
            # print('Timeout isn\'t passed')
            return updates
        updates[sub['id']] = {}
        updates['timeout_passed'] = True
        # [None] means current week
        if initial:
            weeks = [None] + strf_list(get_weeks_range(INITIAL_WEEKS_DEPTH))
        else:
            weeks = [None] + strf_list(get_weeks_range(WEEKS_DEPTH))
        for week in weeks:
            lessons = collect_lessons_data(sub['facultie'], sub['id'], params={'date': week} if week != None else {})
            if not lessons:
                continue
            upd = s.check_add_lessons(lessons, sub_id=str(sub['_id']))
            updates[sub['id']] = merge_dictionaries(updates[sub['id']], upd)
            u.update_subscription_acces_time(sub['_id'])
    return updates


@app.task(name='deferred.get_all_subscibtions_data')
def get_all_subscibtions_data(force=False):
    with UserStandalone() as u:
        res = group([process_sub.s(i, force=force) for i in u.get_all_subs(string_id=True)]).delay()
    return res

@app.task(name='deferred.get_subscribtion')
def get_subscribtion(sub_id, initial=False):
    with UserStandalone() as u:
        res = process_sub.delay(u.get_sub_by_string_id(sub_id=sub_id, string_id=True),  initial=initial)
    return res


@app.task(name='deferred.get_user_subscribtion')
def get_user_subscribtion(tel_user):
    with UserStandalone() as u:
        res = group([process_sub.s(i) for i in u.get_subscriptions(tel_user=tel_user, string_id=True)]).delay()
    # updates = process_subs(s, u, u.get_subscriptions(tel_user=tel_user))
        return res


@app.task(name='deferred.get_teacher_search')
def get_teacher_search(name):
    return get_teachers(name)


@app.task(name='deferred.get_teacher_lessons')
def get_teacher_lessons(id_, params=None):
    return get_teacher_rasp(id_, params=params)


@app.task(name='deferred.unlink_non_used_subs')
def unlink_non_used_subs():
    with StudiesStandalone() as s, \
            UserStandalone() as u:
        unused = u.get_unused_subscriptions()
        lessons_rem = s.remove_lessons_by_subscriptions([un['_id'] for un in unused])
        subs_rem = u.delete_unused_subscriptions()
    return {'lessons': lessons_rem, 'subscriptions': subs_rem}

@app.task(name='deferred.purge_subscription_timeouts')
def purge_subscription_timeouts():
    with UserStandalone() as u:
        return u.purge_subscription_timeouts().raw_result

@app.task(name='deferred.notify_users')
def notify_users():
    with StudiesStandalone() as s, \
            UserStandalone() as u:
        for user_sub_set in u.get_all_users_subscription_settings():
            for sub, setting in user_sub_set.items():
                if setting['notify']:
                    print(s.get_lessons_by_subscription_in_range(sub, datetime.now(), datetime.now()+timedelta(days=3)))
            # sub, settings = list(sub_set.items())
            #
            # print(sub)
            # print(type(settings))
            # if settings['notify']:
            #     print(s.get_lessons_by_subscription_in_time(sub, datetime.now(), timedelta(days=10)))
