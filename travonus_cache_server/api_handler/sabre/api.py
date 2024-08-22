from django.conf import settings
from api_handler.utils import call_external_api
from asgiref.sync import sync_to_async
from api_handler.models import ApiCredentials
from django.http import JsonResponse
import json
import threading

from api_handler.sabre.translators import (
    air_search_translate,
    search_result_translate,
    air_rules_inject_translate,
    air_rules_result_translate,
    air_pricing_details_inject_translate,
    flight_booking_inject_translate,
    flight_booking_result_translate,
)
from api_handler.sabre.serializers import AuthenticationSerializer
from api_handler.sabre import urls
from api_handler.sabre.create_session import create_session
from api_handler.utils import get_best_match_flight
import concurrent.futures

from django.utils import timezone

#########
# Sabre #
#########


def authenticate(request):

    api_response = call_external_api(
        ssl=False,
        url=urls.AUTHENTICATION_URL,
        method="POST",
        data={"Accept": "*/*", "grant_type": "client_credentials"},
        content="data",
        headers={
            "Authorization": f"Basic {settings.SABRE_TOKEN_SANDBOX}",
            # "Authorization": f"Basic {settings.SABRE_TOKEN}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    print(api_response)

    api_response = AuthenticationSerializer(data=api_response)

    if api_response.is_valid(raise_exception=True):
        print(api_response.data)

        expiry_date = timezone.now() + timezone.timedelta(
            seconds=api_response.data.get("expires_in")
        )

        # store it to DB
        ApiCredentials.objects.update_or_create(
            api_name="sabre",
            defaults={
                "token": api_response.data.get("access_token"),
                "expiry_date": expiry_date,
            },
        )
        return JsonResponse({"data": "ok"})

    return JsonResponse({"data": "error"})


def air_search(search_params: dict):
    # general format to sabre native format
    body = air_search_translate(search_params=search_params)

    # pretty print json
    # print(json.dumps(body, indent=4))

    token = ApiCredentials.objects.get(api_name="sabre").token
    api_response = call_external_api(
        urls.AIR_SEARCH_URL,
        method="POST",
        data=body,
        headers={"Authorization": f"Bearer {token}"},
        ssl=False,
    )

    return search_result_translate(api_response, search_params)


def pricing_details(pricing_params: dict):
    """
    First step: re-search the flight with meta_data
    Second step: get the best match flight
    Third step: get the pricing details
    """

    results = air_search(pricing_params["meta_data"])
    best_match_flight = get_best_match_flight(results, pricing_params)

    print(json.dumps(best_match_flight, indent=4))

    body = air_pricing_details_inject_translate(pricing_params=best_match_flight)
    print(json.dumps(body, indent=4))

    token = ApiCredentials.objects.get(api_name="sabre").token
    api_response = call_external_api(
        urls.AIR_PRICING_DETAILS_URL,
        method="POST",
        data=body,
        headers={"Authorization": f"Bearer {token}"},
        ssl=False,
    )

    print(api_response)
    return search_result_translate(api_response, pricing_params["meta_data"])
