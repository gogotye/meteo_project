from django.urls import path
from .views import autocomplete_city_geo


app_name = 'search_field_autocomplete'


urlpatterns = [
    path('search-field/', autocomplete_city_geo, name='autocomplete_city'),
]