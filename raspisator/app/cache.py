
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
        return self.r.set(_week(user_id), week_monday.strftime("%Y-%m-%d %H:%M"))

    def get_user_week(self, user_id):
        try:
            msg = self.r.get(_week(user_id))
            if not msg:
                return None
            w = datetime.strptime(msg.decode('utf-8'), "%Y-%m-%d %H:%M")
        except TypeError:
            return None
        else:
            return w

    def set_user_cal(self, user_id, cal):
        return self.r.set(_cal(user_id), json.dumps(cal))

    def get_user_cal(self, user_id):
        try:
            msg = self.r.get(_cal(user_id))
            if not msg:
                return None
            c = json.loads(msg)
        except TypeError:
            return None
        else:
            return c

    def set_user_curr_gr(self, user_id, group):
        return self.r.set(_gr(user_id), group)

    def get_user_curr_gr(self, user_id):
        try:
            msg = self.r.get(_gr(user_id))
            if not msg:
                return None
            g = msg.decode('utf-8')
        except TypeError:
            return None
        else:
            return g
