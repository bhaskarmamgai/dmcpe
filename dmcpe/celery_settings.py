# Celery settings for async task processing

# Celery Configuration
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'

# Task serialization
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Timezone
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Task result expiration (1 hour)
CELERY_RESULT_EXPIRES = 3600

# Task execution settings
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes max per task
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes soft limit

# Worker settings
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Task routing (optional - for multiple queues)
CELERY_TASK_ROUTES = {
    'conversations.tasks.process_message_async': {'queue': 'quotes'},
    'conversations.tasks.process_quote_modification_async': {'queue': 'quotes'},
}

# Beat schedule (for periodic tasks - optional)
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Example: Clean up old tasks every day at midnight
    'cleanup-old-tasks': {
        'task': 'conversations.tasks.cleanup_old_tasks',
        'schedule': crontab(hour=0, minute=0),
    },
}
