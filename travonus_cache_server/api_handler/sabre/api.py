from django.conf import settings
from api_handler.utils import call_external_api
from api_handler.models import ApiCredentials
from django.http import JsonResponse
import json
import threading
from decimal import Decimal
from api_handler.utils import get_best_match_flight
from api_handler.sabre.translators import (
    air_search_translate,
    search_result_translate,
    air_rules_mini_inject_translate,
    air_rules_mini_result_translate,
    air_pricing_details_inject_translate,
    air_pricing_details_result_translate,
    flight_booking_inject_translate,
    flight_booking_result_translate,
    flight_pre_booking_result_translate,
)

# from agent.models import AgentMarkup
from api_handler.sabre.serializers import AuthenticationSerializer
from api_handler.sabre import urls
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


def air_search(
    search_params: dict,
    tracing_id: str,
    admin_markup: Decimal,
    agent_markup_instance=None,
):
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

    return search_result_translate(
        results=api_response,
        search_params=search_params,
        tracing_id=tracing_id,
        admin_markup=admin_markup,
        agent_markup_instance=agent_markup_instance,
    )


def air_rules_individual(obj: dict):
    body = call_external_api(
        urls.XML_BASE_URL,
        obj["xml"],
        False,
        "POST",
        "data",
        headers={
            "Content-Type": "text/xml; charset=utf-8",
        },
    )

    return {
        "route": obj["route"],
        "body": body,
    }


# -------------- Air Rules --------------
def mini_air_rules(rules_params: dict):
    body = air_rules_mini_inject_translate(rules_params=rules_params)

    token = ApiCredentials.objects.get(api_name="sabre").token
    api_response = call_external_api(
        urls.AIR_PRICING_DETAILS_URL,
        method="POST",
        data=body,
        headers={"Authorization": f"Bearer {token}"},
        ssl=False,
    )

    return air_rules_mini_result_translate(
        rules_params=api_response, meta_data=rules_params["meta_data"]
    )


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
