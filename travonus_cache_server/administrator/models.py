from django.db import models


class MobileAdminInfo(models.Model):
    admin_markup = models.DecimalField(max_digits=5, decimal_places=2)
    updated_on = models.DateTimeField(auto_now=True)
