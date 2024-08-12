from django.contrib import admin
from .models import ApiCredentials, SessionToken


@admin.register(ApiCredentials)
class ApiCredentialsAdmin(admin.ModelAdmin):
    list_display = (
        "api_name",
        "token",
        "created_on",
        "expiry_date",
    )
    search_fields = ("first_name", "last_name", "email", "token_id")
    readonly_fields = ("created_on",)
    list_filter = ("created_on", "expiry_date")


@admin.register(SessionToken)
class SessionTokenAdmin(admin.ModelAdmin):
    list_display = ("token", "created_on")
    search_fields = ("token",)
    readonly_fields = ("created_on",)
