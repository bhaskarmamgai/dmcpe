from django.conf import settings
import redis


if hasattr(settings, 'REDIS_HOST_LMS'):
    lms_redis_instance = redis.StrictRedis(host=settings.REDIS_HOST_LMS,
                                           port=settings.REDIS_PORT_LMS)


def get_redis_instance():
    return redis.StrictRedis(host=settings.REDIS_HOST_LMS,
                             port=settings.REDIS_PORT_LMS)


def convert(data):
    if isinstance(data, bytes):  return data.decode('utf-8')
    if isinstance(data, dict):   return dict(map(convert, data.items()))
    if isinstance(data, tuple):  return map(convert, data)
    return data


def get_hmset_data(key: str):
    if get_redis_instance().exists(key):
        return dict(map(convert, get_redis_instance().hgetall(key).items()))
    return False


def put_data_via_hmset(key: str, data, ttl):
    get_redis_instance().hmset(key, data)
    return get_redis_instance().expire(key, ttl)


def push_data_via_hmset(key: str, data, ttl, ):
    get_redis_instance().delete(key)
    get_redis_instance().hmset(key, data)
    return get_redis_instance().expire(key, ttl)


# "Returns the number of seconds until the key ``name`` will expire"
def get_remaining_time(key):
    return get_redis_instance().ttl(key)


def delete_key_from_redis(key):
    if get_redis_instance().exists(key):
        return get_redis_instance().delete(key)
