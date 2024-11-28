from decimal import Decimal
from django.conf import settings
from api_handler.utils import call_external_api
from api_handler.flyhub.serializers import AuthenticationSerializer
from api_handler.flyhub import urls
from api_handler.models import ApiCredentials
from django.http import JsonResponse
from api_handler.utils import get_best_match_flight
from api_handler.flyhub.translators import (
    air_search_translate,
    search_result_translate,
    air_rules_inject_translate,
    air_rules_result_translate,
    flight_booking_inject_translate,
    flight_pre_booking_result_translate,
    flight_booking_result_translate,
    flight_ticket_inject_translate,
)
import json


##########
# Flyhub #
##########


def authenticate(request):
    print("Flyhub Auth -------------------")
    data = {
        "username": settings.FLYHUB_USERNAME,
        "apikey": settings.FLYHUB_APIKEY,
    }

    api_response = call_external_api(urls.AUTHENTICATION_URL, data, method="POST")

    api_response = AuthenticationSerializer(data=api_response)

    if api_response.is_valid(raise_exception=True):
        print(api_response.data)

        # store it to DB
        if not (
            api_response.data.get("TokenId") == ""
            or api_response.data.get("TokenId") == None
        ):
            ApiCredentials.objects.update_or_create(
                api_name="flyhub",
                defaults={
                    "token": api_response.data.get("TokenId"),
                    "expiry_date": api_response.data.get("ExpireTime"),
                },
            )

            return JsonResponse({"data": "ok"})

    return JsonResponse({"data": "error"})


def air_search(search_params: dict):
    # general format to flyhub native format
    body = air_search_translate(search_params=search_params)

    token = ApiCredentials.objects.get(api_name="flyhub").token
    api_response = call_external_api(
        urls.AIR_SEARCH_URL,
        method="POST",
        data=body,
        headers={"Authorization": f"Bearer {token}"},
        ssl=True,
    )

    return search_result_translate(api_response, search_params)


def pricing_details(
    pricing_params: dict,
    admin_markup: Decimal,
    agent_markup_instance=None,
):
    results = air_search(
        search_params=pricing_params["meta_data"],
        tracing_id=pricing_params["trace_id"],
        admin_markup=admin_markup,
        agent_markup_instance=agent_markup_instance,
    )
    if results is []:
        return []

    best_match_flight = get_best_match_flight(results, pricing_params)
    if best_match_flight is None:
        return []

    print(json.dumps(best_match_flight, indent=4))
    return best_match_flight

    # body = air_rules_inject_translate(rules_params=best_match_flight)
    # print(json.dumps(body, indent=4))

    # token = ApiCredentials.objects.get(api_name="flyhub").token
    # api_response = call_external_api(
    #     urls.AIR_PRICING_DETAILS_URL,
    #     method="POST",
    #     data=body,
    #     headers={"Authorization": f"Bearer {token}"},
    #     ssl=False,
    # )
    # print(json.dumps(api_response, indent=4))
    # return search_result_translate(api_response, pricing_params["meta_data"])
