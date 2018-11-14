
from redis import Redis
from datetime import timedelta, datetime
import json

def _week(uid):
    return 'week-{0}'.format(uid)

def _cal(uid):
    return 'cal-{0}'.format(uid)

def _gr(uid):
    return 'group-{0}'.format(uid)

class Cache:

    def __init__(self, redis: Redis):
        self.r = redis

    def set_user_week(self, user_id, week_monday):
        return self.r.set(_week(user_id), week_monday.strftime("%Y-%m-%d %H:%M"), ex=timedelta(minutes=3))

    def get_user_week(self, user_id):
        try:
            w = datetime.strptime(self.r.get(_week(user_id)).decode('utf-8'), "%Y-%m-%d %H:%M")
        except TypeError:
            return None
        else:
            return w

    def set_user_cal(self, user_id, cal):
        return self.r.set(_cal(user_id), json.dumps(cal), ex=timedelta(minutes=3))

    def get_user_cal(self, user_id):
        try:
         c = json.loads(self.r.get(_cal(user_id)))
        except TypeError:
            return None
        else:
            return c

    def set_user_curr_gr(self, user_id, group):
        return self.r.set(_gr(user_id), group, ex=timedelta(minutes=3))

    def get_user_curr_gr(self, user_id):
        return self.r.get(_gr(user_id))
