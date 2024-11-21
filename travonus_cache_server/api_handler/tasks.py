# yourapp/tasks.py
from celery import shared_task
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from api_handler.flyhub.api import authenticate as flyhub_authenticate
from api_handler.sabre.api import authenticate as sabre_authenticate

# Result caching
from api_handler.flyhub.api import air_search as flyhub_air_search
from api_handler.sabre.api import air_search as sabre_air_search
from api_handler.bdfare.api import air_search as bdfare_air_search
from api_handler.utils import ALL_AIRLINES, get_search_payload
from api_handler.utils import store_in_redis, remove_all_flights
from django.utils import timezone
from datetime import timedelta
import concurrent.futures


@shared_task
def update_token():
    flyhub_authenticate()
    sabre_authenticate()


@shared_task
def store_in_cache():
    remove_all_flights()
    start_date = timezone.now()

    # Store the results for the next 7 days
    for i in range(7):
        for origin, destination in ALL_AIRLINES:
            current_date = start_date + timedelta(days=i)
            search_payload = get_search_payload(
                origin=origin,
                destination=destination,
                departure_date=current_date.strftime("%Y-%m-%d"),
            )
            result = []

            # Threading requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(bdfare_air_search, search_payload),
                    executor.submit(sabre_air_search, search_payload),
                    # executor.submit(flyhub_air_search, search_payload),
                ]

                for future in concurrent.futures.as_completed(futures):
                    result.extend(future.result())

            print("\n-------------------- Storing in redis ----------------------")
            print(f"Storing in cache for: {current_date}")
            print(f"Origin: {origin}, Destination: {destination}")
            print(f"result: {len(result)}")
            store_in_redis(result)

# --------------- for updating the tokens ---------------
schedule, _ = IntervalSchedule.objects.get_or_create(
    every=5,
    period=IntervalSchedule.DAYS,
)

# Schedule the periodic task programmatically
periodic_task_instance, created = PeriodicTask.objects.get_or_create(
    name="Update Token",
    defaults={
        'task': "api_handler.tasks.update_token",
        'interval': schedule,
    }
)

# If the task already exists, you may want to update it
if not created:
    periodic_task_instance.interval = schedule
    periodic_task_instance.task = "api_handler.tasks.update_token"
    periodic_task_instance.save()

# --------------- for storing flight results in cache ---------------
crontab_schedule, _ = CrontabSchedule.objects.get_or_create(
    hour="17",
    minute="00",
    day_of_week="*",
    day_of_month="*",
    month_of_year="*",
)

# Schedule the periodic task programmatically
cache_task_instance, created = PeriodicTask.objects.get_or_create(
    name="Store in Cache",
    defaults={
        'task': "api_handler.tasks.store_in_cache",
        'crontab': crontab_schedule,
    }
)

# If the task already exists, update it
if not created:
    cache_task_instance.crontab = crontab_schedule
    cache_task_instance.task = "api_handler.tasks.store_in_cache"
    cache_task_instance.save()