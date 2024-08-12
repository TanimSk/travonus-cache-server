# yourapp/tasks.py
from celery import shared_task
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from api_handler.flyhub.api import authenticate


@shared_task
def update_token():
    # flyhub
    authenticate()


schedule, created = IntervalSchedule.objects.get_or_create(
    every=5,
    period=IntervalSchedule.DAYS,
)
# Schedule the periodic task programmatically
PeriodicTask.objects.get_or_create(
    name="Update Token",
    task="api_handler.tasks.update_token",
    interval=schedule,
)
