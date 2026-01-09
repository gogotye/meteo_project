from .views import TotalCitySearchedView
from django.urls import path


app_name = 'weather_api'


urlpatterns = [
    path('total-city-searched/', TotalCitySearchedView.as_view(), name='total_search'),
]