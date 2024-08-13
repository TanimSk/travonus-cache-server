import celery
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travonus_cache_server.settings")
app = celery.Celery("travonus_cache_server")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


# celery -A travonus_cache_server worker -l INFO
# celery -A travonus_cache_server beat -l INFO
