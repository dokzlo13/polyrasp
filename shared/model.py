
from bson.objectid import ObjectId

import collections
import hashlib
from pymongo import MongoClient
from datetime import timedelta, datetime

class Userdata:
    def __init__(self, db):
        self.users = db.get_collection('users')
        self.subscriptions = db.get_collection('subscriptions')

    def create_or_get_user(self, tele_user_id, user_name):
        user = self.users.find_one({'uid': tele_user_id, "name": user_name})
        if user:
            return user['_id']
        else:
            return self.users.insert_one({'uid': tele_user_id,
                                          'name': user_name,
                                          'subscription': [],
                                          'settings': {},
                                          'subscription_settings': {'default_group': None}
                                          }).inserted_id

    def add_subscription(self, tel_user_id, sub, message_chat_id):
        # sub.update({'notification': True})
        existed_sub = self.get_sub_by_group_id(sub['id'])
        if not existed_sub:
            sub = self.subscriptions.insert_one(sub).inserted_id
        else:
            sub = existed_sub['_id']

        settings = {
            'chat': message_chat_id,
            'notify': True,
            'default': False
        }

        self.users.update({'uid': tel_user_id},
                          {'$addToSet': {'subscription': sub}})
        self.users.update({'uid': tel_user_id},
                {'$set': {'subscription_settings.' + str(sub): settings}},
        )
        return sub

    def get_user_by_tel_id(self, user_id):
        return self.users.find_one({'uid': int(user_id)})

    def get_sub_by_group_id(self, group_id):
        return self.subscriptions.find_one({'id': int(group_id)})

    def get_sub_by_string_id(self, sub_id):
        return self.subscriptions.find_one({'_id': ObjectId(sub_id)})

    def get_all_subs(self):
        return self.subscriptions.find()

    def update_subscription_acces_time(self, sub_id):
        self.subscriptions.update({'_id': ObjectId(sub_id) if isinstance(sub_id, str) else sub_id}, {'$set': {'upd_time': datetime.now()}})

    def delete_subscription(self, tel_user, sub_id):
        subs = self.get_subscriptions(tel_user=tel_user, sub_id=sub_id)
        if subs == []:
            return
        for sub in subs:
            if sub['_id'] == ObjectId(sub_id) if isinstance(sub_id, str) else sub_id:
                # self.subscriptions.remove({'_id': ObjectId(sub_id) if isinstance(sub_id, str) else sub_id})
                self.users.update({'uid': int(tel_user)}, {'$pull': {'subscription': ObjectId(sub_id) if isinstance(sub_id, str) else sub_id}})
                self.users.update({'uid': int(tel_user)}, {"$unset": {'subscription_settings.'+str(sub_id): ""} })
                return sub['name']

    def get_user_subscription_settings(self, tel_user=None, sub_id=None):
        subs = self.get_subscriptions(tel_user=tel_user, sub_id=sub_id)
        if subs:
            sub = str(subs[0]['_id'])
        else:
            return
        user = self.users.find_one({'uid':tel_user})
        return subs[0], user['subscription_settings'][sub]

    def change_notification_state(self, tel_user, sub_id):
        sub, settings = self.get_user_subscription_settings(tel_user, sub_id)
        print(settings)
        self.users.update({'uid': tel_user}, {'$set': {'subscription_settings.'+str(sub['_id'])+'.notify': not settings['notify']}})
        sub.update({"notify": not settings['notify']})
        return sub, settings

    def get_subscriptions(self, *, tel_user=None, db_user=None, sub_id=None):

        query = [
                {'$match': {'uid': int(tel_user)}} if tel_user else {'$match': {'_id': db_user}},
                {'$lookup':
                    {
                        'from': 'subscriptions',
                        'localField': 'subscription',
                        "foreignField": "_id",
                        'as': 'subscription'
                    }
                },
                {'$project': {'subscription': 1, '_id':0}},
            ]

        if sub_id:
            query.append({"$unwind": "$subscription"})
            query.append({'$match': {'subscription._id': ObjectId(sub_id)}})

        subs = self.users.aggregate(query)
        try:
            subs = next(subs)
        except StopIteration:
            return []
        else:
            if isinstance(subs['subscription'], (list, tuple)):
                return subs['subscription']
            else:
                return [subs['subscription']]

    def get_all_users_subscribes(self):
        data = []
        raw = self.users.find({}, {'subscription':1, '_id':0})
        for item in raw:
            data.extend(item['subscription'])
        return data

    def get_all_users_subscription_settings(self):
        data = []
        raw = self.users.find({}, {"subscription_settings" :1, '_id':0})
        for item in raw:
            data.append(item["subscription_settings"])
        return data

    def get_unused_subscriptions(self):
        return list(self.subscriptions.find({'_id': {"$nin": self.get_all_users_subscribes()}}))

    def delete_unused_subscriptions(self):
        return self.subscriptions.remove({'_id': {'$in': [i['_id'] for i in self.get_unused_subscriptions()]}})

    def purge_subscription_timeouts(self):
        return self.subscriptions.update_many({}, {'$set': {'upd_time': datetime.min}})

    def get_user_default_group(self, tel_user):
        return str(next(self.users.find({'uid': int(tel_user)}))['settings']['default_group'])

    def unset_all_default_groups(self, tel_user):
        self.users.update({'uid': tel_user},
                          {'$set': {'settings.default_group': ''}},
        )
        for sub in map(str, next(self.users.find({'uid': tel_user}))['subscription']):
            self.users.update({'uid': int(tel_user)},  {'$set': {'subscription_settings.'+ sub +'.default': False}})


    def set_user_default_group(self, tel_user, group_id):
        self.unset_all_default_groups(tel_user)
        self.users.update({'uid': tel_user},
                          {'$set': {'settings.default_group': ObjectId(group_id)}},
                          # {'$set': {'"subscription_settings.'+str(group_id)+'.default': True}},
        )
        self.users.update({'uid': tel_user},
                          # {'$set': {'settings.default_group': ObjectId(group_id)}},
                          {'$set': {'subscription_settings.'+str(group_id)+'.default': True}},
        )


class Studiesdata:
    def __init__(self, db):
        self.db = db
        self.faculties = db.get_collection('faculties')
        self.groups = db.get_collection('groups')
        self.lessons = db.get_collection('lessons')

    def update_faculties(self, data):
        return self.faculties.insert_many(data)

    def update_groups(self, data):
        return self.groups.insert_many(data)

    def get_faculties_names(self):
        faculties = self.faculties.aggregate([{'$project': {'name':1, '_id':0}}])
        return [i['name'] for i in faculties]

    def get_facultie_by_facultie_name(self, fac_name):
        return self.faculties.find_one({"name" : fac_name})

    def get_facult_by_react_id(self, fac_id):
        if isinstance(fac_id, (list, tuple)):
            return self.faculties.find({'id': {'$in': fac_id}})
        else:
            return self.faculties.find_one({'id': fac_id})

    def get_group_by_name(self, group_name):
        return self.groups.find_one({'name': group_name})

    def get_groups_by(self, type_=None, fac_id=None, level=None, kind=None):
        query = {}
        if type_:
            query.update({'type': type_})
        if fac_id:
            query.update({'facultie': fac_id})
        if level:
            query.update({'level': level})
        if kind:
            query.update({'kind': kind})

        return list(self.groups.find(query))

    def add_lessons(self, data):
        return self.lessons.insert_many(data)

    def check_add_lessons(self, data, sub_id=None, checksums_check=True, matches_check=True):
        counter_same = 0
        counter_update = 0

        checksum_cleared_data= []
        for item in data:
            checksum = sha256(gen_checkstring(item))
            item['checksum'] = checksum
            item['upd_time'] = datetime.now()
            if sub_id:
                item['sub_id'] = sub_id

            if checksums_check:
                existed = self.lessons.find_one({'checksum': checksum})
                if existed:
                    counter_same += 1
                    self.lessons.update({'_id': existed['_id']}, {'$set': {'upd_time': datetime.now()}})
                    continue
                else:
                    checksum_cleared_data.append(item)
            else:
                checksum_cleared_data.append(item)

        clear_data = []
        for item in checksum_cleared_data:
            if matches_check:
                existed = self.lessons.find_one({
                    "time_start": item["time_start"],
                   "time_end": item["time_end"],
                   "groups.id": {'$in' :[gr['id'] for gr in item["groups"]]},
                   "weekday": item["weekday"]
                })

                if existed:
                    self.lessons.update({'_id': existed['_id']}, item)
                    counter_update += 1
                    data.remove(item)
                else:
                    clear_data.append(item)
            else:
                clear_data.append(item)

        inserted = 0
        if clear_data:
            inserted = len(self.add_lessons(data).inserted_ids)
        return {'new': inserted, 'same': counter_same, 'updated': counter_update}

    def get_lessons_in_day(self, group_id:int, day: datetime):
        return list(self.lessons.find({'groups.id':group_id,
                                       '$and': [{"time_start": {'$gte': day}},
                                                {"time_start": {'$lte': day+timedelta(days=1)}}]
                                       }))

    def get_nearest_lesson(self, group_id, delta=None):
        delta = delta or timedelta(days=7)
        return self.lessons.find_one({'groups.id': group_id,
                                  "time_start":{'$gte': datetime.now(), '$lt': datetime.now() + delta}},
                                 {'checksum': 0, '_id':0},)

    def get_lessons_by_subscription_by_delta(self, sub_id, date, delta):
        q = {"sub_id": str(sub_id)}
        q.update({'$and':
                     [{"time_start": {'$gte': date - delta}},
                      {"time_start": {'$lte': date + delta}}]
                 }
                 )
        return list(self.lessons.find(q))

    def get_lessons_by_subscription_in_range(self, sub_id, from_, to):
        q = {"sub_id": str(sub_id)}
        q.update({'$and':
                     [{"time_start": {'$gte': from_}},
                      {"time_start": {'$lte': to}}]
                 }
                 )
        return list(self.lessons.find(q))

    def remove_lessons_by_subscriptions(self, sub_ids:list):
        return self.lessons.remove({'sub_id': {'$in': [str(sub_id) for sub_id in sub_ids]}})

def gen_checkstring(dict_: dict) -> str:
    dict_ = collections.OrderedDict(sorted(dict_.items()))
    checkstr = ''
    for v in dict_.values():
        if isinstance(v, (list,tuple)):
            for subv in v:
                if isinstance(subv, dict):
                    checkstr += gen_checkstring(subv)
        elif isinstance(v, dict):
            checkstr += gen_checkstring(v)
        elif isinstance(v, int):
            checkstr += str(v)
        elif isinstance(v, datetime):
            checkstr += v.strftime('%Y%m%d%H%M%S')
        elif isinstance(v, str):
            checkstr += v
    return checkstr

def sha256(w):
    h = hashlib.sha256(w.encode('utf-8'))
    return h.hexdigest()

def context_model(model, connection, db):
    class context_model:
        def __init__(self, **kwargs):
            self._kwargs = kwargs

        def __enter__(self):
            self.conn = MongoClient(connection)
            if hasattr(self._kwargs, 'purge_schema') and self._kwargs['purge_schema']:
                for collection in self._kwargs['purge_schema']:
                    self.conn.drop_database(collection)
            self.model = model(self.conn.get_database(db))
            return self.model

        def __exit__(self, exc_type, exc_val, exc_tb):
            del self.model
            self.conn.close()

    return context_model
