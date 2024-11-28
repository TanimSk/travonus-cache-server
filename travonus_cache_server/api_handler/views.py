from rest_framework.views import APIView
from django.http import JsonResponse
import concurrent.futures

# from django.conf import settings
from administrator.models import MobileAdminInfo
from redis.commands.search.query import Query
from api_handler.utils import store_in_redis, redis_client, remove_all_flights
from api_handler.models import ApiCredentials
from api_handler.utils import call_external_api
from api_handler.sabre import urls
import json

# Serializers
from api_handler.serializers import AirSearchSerializer, AirRulesSerializer

# 1. Search
# from api_handler.flyhub.api import air_search as flyhub_air_search
# from api_handler.sabre.api import air_search as sabre_air_search
# from api_handler.bdfare.api import air_search as bdfare_air_search

# 2. Rules
# from api_handler.bdfare.api import air_rules as bdfare_air_rules
# from api_handler.flyhub.api import air_rules as flyhub_air_rules
# from api_handler.sabre.api import air_rules as sabre_air_rules

# 3. Pricing Details
from api_handler.bdfare.api import pricing_details as bdfare_pricing_details
from api_handler.flyhub.api import pricing_details as flyhub_pricing_details
from api_handler.sabre.api import pricing_details as sabre_pricing_details


class CacheAirSearch(APIView):
    serializer_class = AirSearchSerializer

    def convert_to_json(self, results):
        flights = []
        for doc in results.docs:
            flight = redis_client.json().get(doc.id)
            flights.append(flight)

        return flights

    def post(self, request, format=None, *args, **kwargs):
        serialized_data = self.serializer_class(data=request.data)

        if serialized_data.is_valid(raise_exception=True):

            result = []
            index_name = "result_cache_idx"

            origin = serialized_data.data["segments"][0]["origin"]
            destination = serialized_data.data["segments"][0]["destination"]
            departure_date = serialized_data.data["segments"][0][
                "departure_date"
            ].replace("-", "\\-")

            query_str = (
                f"@origin:{origin} "
                f"@destination:{destination} "
                f"@departure_date:{{{departure_date}}}"
            )

            # filter by refundable
            if (
                request.GET.get("is_refundable", False) == "true"
                or request.GET.get("is_refundable", False) == "false"
            ):
                query_str = (
                    f"{query_str} @is_refundable:{{{request.GET.get('is_refundable')}}}"
                )

            # filter by range
            if request.GET.get("min", False) and request.GET.get("max", False):
                query_str = f"{query_str} @total_fare:[{int(request.GET.get('min'))} {int(request.GET.get('max'))}]"

            print(query_str)

            # query in redisearch
            query = (
                Query(query_string=query_str)
                .sort_by("total_fare", asc=True)
                .paging(0, 100)
            )
            result = redis_client.ft(index_name).search(query)
            result = self.convert_to_json(result)

            return JsonResponse(result, safe=False)


class ClearCacheAPI(APIView):
    def post(self, request, format=None, *args, **kwargs):
        remove_all_flights()
        return JsonResponse({"message": "Cache cleared"}, safe=False)


class PricingDetails(APIView):
    # serializer_class = AirRulesSerializer

    def post(self, request, format=None, *args, **kwargs):
        # serialized_data = self.serializer_class(data=request.data)
        # if serialized_data.is_valid(raise_exception=True):
        admin_markup = MobileAdminInfo.objects.first().admin_markup

        serialized_data = request
        result = []

        if serialized_data.data["api_name"] == "bdfare":
            result = bdfare_pricing_details(serialized_data.data, admin_markup)
        elif serialized_data.data["api_name"] == "flyhub":
            result = flyhub_pricing_details(serialized_data.data, admin_markup)
        elif serialized_data.data["api_name"] == "sabre":
            result = sabre_pricing_details(serialized_data.data, admin_markup)

        return JsonResponse(result, safe=False)
