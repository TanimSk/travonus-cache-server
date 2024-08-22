from django.conf import settings
from api_handler.utils import call_external_api

# from asgiref.sync import sync_to_async
# from api_handler.models import ApiCredentials
# from django.http import JsonResponse
from api_handler.utils import get_best_match_flight
from api_handler.bdfare.translators import (
    air_search_translate,
    search_result_translate,
    air_rules_inject_translate,
    air_rules_result_translate,
    air_pricing_details_inject_translate,
    flight_booking_inject_translate,
    flight_pre_booking_result_translate,
    flight_booking_result_translate,
)
from api_handler.bdfare import urls
import json


##########
# BDfare #
##########


def air_search(search_params: dict):
    # general format to sabre native format
    body = air_search_translate(search_params=search_params)

    print(json.dumps(body, indent=4))

    api_response = call_external_api(
        urls.AIR_SEARCH_URL,
        method="POST",
        data=body,
        headers={"X-API-KEY": settings.BDFARE_TOKEN},
        ssl=False,
    )
    # print(api_response)
    return search_result_translate(api_response, search_params)


def pricing_details(pricing_params: dict):
    """
    First step: re-search the flight with meta_data
    Second step: get the best match flight
    Third step: get the pricing details
    """

    results = air_search(pricing_params["meta_data"])
    best_match_flight = get_best_match_flight(results, pricing_params)

    body = air_pricing_details_inject_translate(pricing_params=best_match_flight)
    print(json.dumps(body, indent=4))

    api_response = call_external_api(
        urls.AIR_PRICING_DETAILS_URL,
        method="POST",
        data=body,
        headers={"X-API-KEY": settings.BDFARE_TOKEN},
        ssl=False,
    )
    print(json.dumps(api_response, indent=4))
    return search_result_translate(api_response, pricing_params["meta_data"])
