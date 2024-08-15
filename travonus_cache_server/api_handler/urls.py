from django.urls import path
from api_handler.views import CacheAirSearch, FareRules, PricingDetails, ClearCacheAPI
from api_handler.flyhub.api import authenticate as flyhub_auth
from api_handler.sabre.api import authenticate as sabre_auth

urlpatterns = [
    path("cache_air_search/", CacheAirSearch.as_view(), name="air_search"),
    path("clear_cache/", ClearCacheAPI.as_view(), name="clear_cache"),
    path("air_rules/", FareRules.as_view(), name="air_rules"),
    path("pricing_details/", PricingDetails.as_view(), name="pricing_details"),
    # for testing
    path("flyhub_auth/", flyhub_auth, name="flyhub_auth"),
    path("sabre_auth/", sabre_auth, name="sabre_auth"),
]
