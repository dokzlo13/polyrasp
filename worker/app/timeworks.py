
from datetime import datetime, timedelta

def timeout_has_passed(sub, renew_time):
    return  sub.get('upd_time') is None or (datetime.now() - sub["upd_time"]).seconds > renew_time

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