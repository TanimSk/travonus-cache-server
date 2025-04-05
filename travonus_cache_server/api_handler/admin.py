from django.contrib import admin
from .models import ApiCredentials


@admin.register(ApiCredentials)
class ApiCredentialsAdmin(admin.ModelAdmin):
    list_display = (
        "api_name",
        "token",
        "updated_on",
        "expiry_date",
    )
    search_fields = ("first_name", "last_name", "email", "token_id")
    readonly_fields = ("updated_on",)
    list_filter = ("updated_on", "expiry_date")
