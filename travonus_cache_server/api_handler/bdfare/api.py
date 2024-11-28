from django.conf import settings
from api_handler.utils import call_external_api

# from asgiref.sync import sync_to_async
# from api_handler.models import ApiCredentials
# from django.http import JsonResponse
from decimal import Decimal
from api_handler.bdfare.translators import (
    air_search_translate,
    process_search_result,
    air_rules_inject_translate,
    air_rules_result_translate,
    air_pricing_details_inject_translate,
    flight_booking_inject_translate,
    flight_pre_booking_result_translate,
    flight_booking_result_translate,
    air_rules_mini_inject_translate,
    air_rules_mini_result_translate,
)
from api_handler.bdfare import urls
from api_handler.utils import get_best_match_flight

# from agent.models import AgentMarkup
# from django.db.models import QuerySet
import json


##########
# BDfare #
##########


def air_search(
    search_params: dict,
    tracing_id: str,
    admin_markup: Decimal,
    agent_markup_instance=None,
):
    # general format to sabre native format
    body = air_search_translate(search_params=search_params)

    api_response = call_external_api(
        urls.AIR_SEARCH_URL,
        method="POST",
        data=body,
        headers={"X-API-KEY": settings.BDFARE_TOKEN},
        ssl=False,
    )
    return process_search_result(
        results=api_response,
        search_params=search_params,
        trace_id=tracing_id,
        admin_markup=admin_markup,
        agent_markup_instance=agent_markup_instance,
    )


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


def mini_air_rules(rules_params: dict) -> dict:
    # general format to sabre native format
    body = air_rules_mini_inject_translate(rules_params=rules_params)
    api_response = call_external_api(
        urls.AIR_MINI_RULES_URL,
        method="POST",
        data=body,
        headers={"X-API-KEY": settings.BDFARE_TOKEN},
        ssl=False,
    )
    # print(api_response)
    return air_rules_mini_result_translate(api_response)


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

    # body = air_pricing_details_inject_translate(pricing_params=pricing_params)
    # print(json.dumps(body, indent=4))

    # api_response = call_external_api(
    #     urls.AIR_PRICING_DETAILS_URL,
    #     method="POST",
    #     data=body,
    #     headers={"X-API-KEY": settings.BDFARE_TOKEN},
    #     ssl=False,
    # )
    # print(json.dumps(api_response, indent=4))
    # return process_search_result(
    #     api_response,
    #     pricing_params["meta_data"],
    #     admin_markup=admin_markup,
    #     agent_markup_instance=agent_markup_instance,
    # )
