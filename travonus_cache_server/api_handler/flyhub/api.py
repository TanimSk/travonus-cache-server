from django.conf import settings
from api_handler.utils import call_external_api
from api_handler.flyhub.serializers import AuthenticationSerializer
from api_handler.flyhub import urls
from api_handler.models import ApiCredentials
from django.http import JsonResponse
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


def air_rules(rules_params: dict):
    # general format to flyhub native format
    body = air_rules_inject_translate(rules_params=rules_params)

    token = ApiCredentials.objects.get(api_name="flyhub").token
    api_response = call_external_api(
        urls.AIR_RULES_URL,
        method="POST",
        data=body,
        headers={"Authorization": f"Bearer {token}"},
        ssl=True,
    )

    return air_rules_result_translate(api_response)


def pricing_details(pricing_params: dict):
    body = air_rules_inject_translate(rules_params=pricing_params)
    print(json.dumps(body, indent=4))

    token = ApiCredentials.objects.get(api_name="flyhub").token
    api_response = call_external_api(
        urls.AIR_PRICING_DETAILS_URL,
        method="POST",
        data=body,
        headers={"Authorization": f"Bearer {token}"},
        ssl=False,
    )
    print(json.dumps(api_response, indent=4))
    return search_result_translate(api_response, pricing_params["meta_data"])


def flight_pre_booking(pre_booking_params: dict):
    body = flight_booking_inject_translate(booking_params=pre_booking_params)
    token = ApiCredentials.objects.get(api_name="flyhub").token
    api_response = call_external_api(
        urls.FLIGHT_PRE_BOOKING_URL,
        method="POST",
        data=body,
        headers={"Authorization": f"Bearer {token}"},
        ssl=False,
    )

    return flight_pre_booking_result_translate(
        api_response, pre_booking_params["flight_ref"]["meta_data"]
    )


def flight_booking(booking_params: dict):
    body = flight_booking_inject_translate(booking_params=booking_params)
    token = ApiCredentials.objects.get(api_name="flyhub").token
    api_response = call_external_api(
        urls.FLIGHT_BOOKING_URL,
        method="POST",
        data=body,
        headers={"Authorization": f"Bearer {token}"},
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


# def flight_ticket(ticket_params: dict):
#     body = flight_ticket_inject_translate(ticket_params=ticket_params)
#     token = ApiCredentials.objects.get(api_name="flyhub").token
#     api_response = call_external_api(
#         urls.FLIGHT_TICKETING_URL,
#         method="POST",
#         data=body,
#         headers={"Authorization": f"Bearer {token}"},
#         ssl=False,
#     )
#     return api_response
