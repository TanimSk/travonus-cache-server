from django.conf import settings
from api_handler.utils import call_external_api
from api_handler.models import ApiCredentials
from django.http import JsonResponse
import json
import threading
from decimal import Decimal

from api_handler.sabre.translators import (
    air_search_translate,
    search_result_translate,
    air_rules_inject_translate,
    air_rules_mini_inject_translate,
    air_rules_mini_result_translate,
    air_rules_result_translate,
    air_pricing_details_inject_translate,
    air_pricing_details_result_translate,
    flight_booking_inject_translate,
    flight_booking_result_translate,
    flight_pre_booking_result_translate,
)
# from agent.models import AgentMarkup
from api_handler.sabre.serializers import AuthenticationSerializer
from api_handler.sabre import urls
from api_handler.sabre.create_session import create_session
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
    agent_markup_instance = None,
):
    # general format to sabre native format
    body = air_search_translate(search_params=search_params)

    # pretty print json
    print(json.dumps(body, indent=4))

    token = ApiCredentials.objects.get(api_name="sabre").token
    api_response = call_external_api(
        urls.AIR_SEARCH_URL,
        method="POST",
        data=body,
        headers={"Authorization": f"Bearer {token}"},
        ssl=False,
    )

    # create a thread for calling `create_session` function
    create_session_thread = threading.Thread(target=create_session)
    create_session_thread.start()

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


def air_rules(rules_params: dict):
    body_list = air_rules_inject_translate(rules_params=rules_params)
    result = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(
                air_rules_individual,
                body,
            )
            for body in body_list
        ]

        for future in concurrent.futures.as_completed(futures):
            result.append(future.result())

    print(result)
    return air_rules_result_translate(result)


def pricing_details(
    pricing_params: dict,
    admin_markup: Decimal,
    agent_markup_instance = None,
):
    body = air_pricing_details_inject_translate(pricing_params=pricing_params)

    token = ApiCredentials.objects.get(api_name="sabre").token
    api_response = call_external_api(
        urls.AIR_PRICING_DETAILS_URL,
        method="POST",
        data=body,
        headers={"Authorization": f"Bearer {token}"},
        ssl=False,
    )

    # print(api_response)
    return air_pricing_details_result_translate(
        results=api_response,
        search_params=pricing_params["meta_data"],
        admin_markup=admin_markup,
        agent_markup_instance=agent_markup_instance,
    )
