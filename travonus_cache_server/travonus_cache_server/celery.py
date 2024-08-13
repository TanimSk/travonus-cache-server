import celery
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "doctors_appointment.settings")
app = celery.Celery("doctors_appointment")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


# celery -A api_handler worker -l INFO
# celery -A api_handler beat -l INFO
