from django.db import models


class ApiCredentials(models.Model):
    api_name = models.CharField(max_length=100, unique=True)
    token = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()


class SessionToken(models.Model):
    token = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
