from django.conf import settings
from api_handler.utils import call_external_api

# from asgiref.sync import sync_to_async
# from api_handler.models import ApiCredentials
# from django.http import JsonResponse

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


def air_rules(rules_params: dict):
    # general format to sabre native format
    body = air_rules_inject_translate(rules_params=rules_params)
    print(json.dumps(body, indent=4))

    api_response = call_external_api(
        urls.AIR_RULES_URL,
        method="POST",
        data=body,
        headers={"X-API-KEY": settings.BDFARE_TOKEN},
        ssl=False,
    )
    # print(api_response)
    return air_rules_result_translate(api_response)


def pricing_details(pricing_params: dict):
    body = air_pricing_details_inject_translate(pricing_params=pricing_params)
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


def flight_pre_booking(pre_booking_params: dict):
    body = flight_booking_inject_translate(booking_params=pre_booking_params)

    api_response = call_external_api(
        urls.FLIGHT_PRE_BOOKING_URL,
        method="POST",
        data=body,
        headers={"X-API-KEY": settings.BDFARE_TOKEN},
        ssl=False,
    )

    return flight_pre_booking_result_translate(
        api_response, pre_booking_params["flight_ref"]["meta_data"]
    )


def flight_booking(booking_params: dict):
    body = flight_booking_inject_translate(booking_params=booking_params)

    api_response = call_external_api(
        urls.FLIGHT_BOOKING_URL,
        method="POST",
        data=body,
        headers={"X-API-KEY": settings.BDFARE_TOKEN},
        ssl=False,
    )

    return (
        {
            "status": "success",
            "result": flight_booking_result_translate(
                api_response, booking_params["flight_ref"]["meta_data"]
            ),
        }
        if api_response is not None
        else {"status": "error"}
    )
