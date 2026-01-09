import json
from datetime import datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import requests

from search_field_autocomplete.utils import is_cyrillic
from search_history.models import HistoryModel
from . import weather_variables


class GeoApiException(Exception):
    pass


def mock_geocoding_api_request():
    json_response = {'results': [
        {
            'id': 524901, 'name': 'Москва', 'latitude': 55.75222, 'longitude': 37.61556, 'elevation': 144.0,
            'feature_code': 'PPLC', 'country_code': 'RU', 'admin1_id': 524894, 'timezone': 'Europe/Moscow',
            'population': 10381222, 'country_id': 2017370, 'country': 'Россия', 'admin1': 'Москва'
        }
    ]}
    return json_response


def formulas_for_weather_values(index: int):
    view_geo_data = {
        0: 'temperature',
        1: 'apparent_temperature',
        2: 'humidity',
        3: 'rain',
        4: 'is_day',
        5: 'wind_speed'
    }
    key_word = view_geo_data.get(index)

    formulas = {
        'temperature': lambda i: 20 + i * 0.5,
        'apparent_temperature': lambda i: 19 + i * 0.5,
        'humidity': lambda i: 60 + i % 10,
        'rain': lambda i: 0.2 * (i % 3),
        'wind_speed': lambda i: 2 + (i % 5),
        'is_day': lambda i: i % 24 < 18,
    }

    formula = formulas.get(key_word)
    return formula


def mock_openmeteo_response(variables_index: int):
    formula = formulas_for_weather_values(index=variables_index)

    values_list = []
    for i in range(48):
        values_list.append(formula(i))

    return values_list


def mock_hourly_variables_test(view_index):
    mock_val = MagicMock()

    weather_data = mock_openmeteo_response(variables_index=view_index)
    if view_index == 1:
        mock_val.ValuesLength.return_value = 48

    mock_val.Values.side_effect = lambda i: weather_data[i]

    mock_val.Values.call_count = 48

    return mock_val


def mock_current_data(view_index):
    current_weather_test_data = [20.77, 19.22, 55, 0.2, 25]

    mock_val = MagicMock()
    mock_val.Value.return_value = current_weather_test_data[view_index]

    return mock_val


def mock_timestamp():
    return datetime.now(tz=ZoneInfo('Europe/Moscow')).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


def expected_hour_rows(forecast_days: int = 2):
    # Часов осталось в текущем дне
    now = datetime.now(tz=ZoneInfo('Europe/Moscow'))
    remaining_today_hours = 24 - now.hour

    # Оставшееся кол-во полных дней
    remaining_forecast_days = forecast_days - 1

    return remaining_today_hours + 24 * remaining_forecast_days


class CityHistoryContextService:
    @staticmethod
    def attach_city_history_to_context(user, context, session):
        """
        функция для добавления истории поиска городов в context для авторизованного
        или неавторизованного пользователя
        """
        if user.is_authenticated:
            history = (
                HistoryModel.objects
                .filter(user=user)
                .values('city', 'country', 'country_code', 'admin', 'forecast_days')
                .order_by('-timestamp')[:5]
            )

            context['city_history'] = history

        # Для неавторизованного пользователя
        else:
            city_history = session.get('city_history')
            if city_history:
                city_history_copy = city_history.copy()
                context['city_history'] = city_history_copy

    @staticmethod
    def add_city_to_session_history(session, city_values_dict):
        """
        Функция добавления города в сессию неавторизованного пользователя
        Если город уже есть в сессии, то добавление не происходит
        """
        city_history = session.get('city_history', [])

        new_entry = {field: city_values_dict[field] for field in weather_variables.SEARCH_FIELDS if city_values_dict.get(field)}

        if new_entry not in city_history:
            city_history.append(new_entry)

        session['city_history'] = city_history[-5:]

    @staticmethod
    def save_anonymous_city_history(city_values_dict):
        """
        Функция добавления города в историю поиска для неавторизованного пользователя
        Нужна для учета кол-ва запросов городов в total-city-searched/
        """

        HistoryModel.objects.create(user=None, **city_values_dict)


def geo_coding_request(city, country_code=None, admin=None):
    """
    Возвращает данные города с заданными параметрами (params).
    Или ошибку, если чnо-то пошло не так.

    """

    geo_url = "https://geocoding-api.open-meteo.com/v1/search"

    params = {
        'name': city,
        'countryCode': country_code,
        'count': 5,
    }

    if is_cyrillic(city):
        params['language'] = 'ru'

    response = requests.get(geo_url, params=params)

    try:
        response.raise_for_status()
    except requests.RequestException as e:
        raise GeoApiException('Ошибка при запросе геоданных') from e

    try:
        data = response.json()
    except json.JSONDecodeError as e:
        raise GeoApiException('Некорректный ответ от геосервиса') from e

    results = data.get('results') or []
    if not results:
        raise GeoApiException('Город не найден')

    # Если передано название области, то происходит выбор конкретного объекта с этой областью
    if admin:
        match_obj = next(geo_obj for geo_obj in data['results'] if admin == geo_obj.get('admin1'))
        if match_obj:
            return match_obj

    results_data = data['results'][0]
    return results_data


def validate_forecast_days(raw_value):
    """
    Возвращает (forecast_days, error_message).

    forecast_days — int или None, если ошибка.
    error_message — str или None, если всё в порядке.
    """
    if not raw_value:
        raw_value = 3
    try:
        forecast_days = int(raw_value)
        if not (1 <= forecast_days <= 16):
            raise ValueError
    except ValueError:
        return None, "Введите корректное количество дней (от 1 до 16)"

    return forecast_days, None


def extract_params(request):
    base = {
        field: request.GET.get(field)
        for field in weather_variables.SEARCH_FIELDS
    }

    extra = {
        k: v
        for k, v in request.GET.items()
        if k not in weather_variables.SEARCH_FIELDS
    }
    total = {**base, **extra}
    return total
