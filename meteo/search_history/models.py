from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class HistoryModel(models.Model):
    user = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    country_code = models.CharField(max_length=10)
    admin = models.CharField(max_length=100)
    forecast_days = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

