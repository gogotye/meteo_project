from django.urls import path
from .views import search_city


app_name = 'weather_search'


urlpatterns = [
    path('', search_city, name='search'),
]
