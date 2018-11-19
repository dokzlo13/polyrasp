
from datetime import datetime, timedelta

def timeout_has_passed(sub, renew_time):
    if  sub.get('upd_time') is None:
        return True
    date = sub['upd_time']
    if isinstance(date, str):
        try:
            date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
    return (datetime.now() - date).seconds > renew_time

def next_weekday(date, weekday):
    day_gap = weekday - date.weekday()
    if day_gap <= 0:
        day_gap += 7
    return date + timedelta(days=day_gap)

def last_weekday(date, weekday):
    day_gap = weekday - date.weekday()
    if day_gap >= 0:
        day_gap -= 7
    return date + timedelta(days=day_gap)


def next_month(year, month):
    month += 1
    if month > 12:
        month = 1
        year += 1
    return year, month

def last_month(year, month):
    month -= 1
    if month < 1:
        month = 12
        year -= 1
    return year, month

def get_mondays_ahead(amount):
    weeks = [datetime.now()]
    for week in range(1, amount+1):
        weeks.append(next_weekday(weeks[week - 1], 0))
    weeks.pop(0)
    return weeks

def get_mondays_behind(amount):
    weeks = [datetime.now()]
    for week in range(1, amount+1):
        weeks.append(last_weekday(weeks[week - 1], 0))
    weeks.pop(0)
    return weeks

def get_weeks_range(depth):
    weeks = []
    # With current week
    weeks.extend(get_mondays_behind(depth+1))
    weeks.extend(get_mondays_ahead(depth))
    return sorted(weeks)

def strf_list(datetime_list):
    return [dat.strftime('%Y-%m-%d') for dat in datetime_list]

def convert_concat_day_and_lesson(lesson: str, weekday: datetime) -> datetime:
    lesson = datetime.strptime(lesson, '%H:%M')
    lesson = lesson.replace(year=weekday.year,
                 month=weekday.month,
                 day=weekday.day)
    return lesson

def full_week(date):
    year, week, dow = date.isocalendar()
    if dow == 1:
        start_date = date
    else:
        start_date = date - timedelta(dow)

    for delta in map(timedelta, range(7)):
        yield start_date + delta