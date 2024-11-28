from django.contrib import admin
from administrator.models import MobileAdminInfo

@admin.register(MobileAdminInfo)
class MobileAdminInfoAdmin(admin.ModelAdmin):
    list_display = ["admin_markup", "updated_on"]    
    