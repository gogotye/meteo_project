import requests
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .utils import is_cyrillic


@require_GET
def autocomplete_city_geo(request):
    """
    Функция обрабатывает запрос автодополнения города
    Принимает параметр 'q', отправляет его в Open-Meteo Geocoding API.

    Возвращает отсортированный по населению список найденных городов.
    Если запрос на кириллице, то использует русский язык результатов.
    """
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse([], safe=False)

    url = "https://geocoding-api.open-meteo.com/v1/search"

    params = {
        "name": query,
        "count": 5,
    }

    if is_cyrillic(query):
        params['language'] = 'ru'

    response = requests.get(url, params=params, timeout=5)

    data = response.json()
    data_results = data.get('results', [])

    data = sorted(data_results, key=lambda x: x.get('population', 0), reverse=True)
    return JsonResponse(data, safe=False)