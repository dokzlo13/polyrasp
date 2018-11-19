
import os
from celery import Celery
from redis import Redis

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
REDIS_CACHE = os.environ.get('REDIS_CACHE', 'redis://localhost:6379/2')

celery = Celery(broker=CELERY_BROKER_URL,
             backend=CELERY_RESULT_BACKEND,
             )
redis = Redis.from_url(REDIS_CACHE)