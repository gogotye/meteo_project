from django.shortcuts import render
import openmeteo_requests
from datetime import datetime
from zoneinfo import ZoneInfo
from .utils import CityHistoryContextService, geo_coding_request, validate_forecast_days, GeoApiException, extract_params
from .weather_variables import VARIABLES_CURRENT, VARIABLES_HOURLY, SEARCH_FIELDS
from collections import defaultdict
from search_history.utils import add_history_city_to_user
import json


def search_city(request):
    context = {}

    extracted_get_parameters = extract_params(request)

    # Добавление последних городов в context
    CityHistoryContextService.attach_city_history_to_context(
        user=request.user,
        context=context,
        session=request.session
    )

    if all(extracted_get_parameters[key] is None for key in extracted_get_parameters):
        return render(request, 'weather_search/search.html', context)

    raw_city = (extracted_get_parameters.get('city')) or ''.strip()
    if not raw_city:
        context['error'] = 'Нужно ввести название города!'
        return render(request, 'weather_search/search.html', context)

    selected_in_autocomplete = extracted_get_parameters.get('selection', '').strip()
    sel = None
    if selected_in_autocomplete:
        try:
            sel = json.loads(selected_in_autocomplete)
        except json.JSONDecodeError:
            pass
    # Ветка с готовой структурой
    if sel:
        city = sel.get("city")
        country_code = sel.get("country_code")
        country = sel.get("country")
        lat = sel.get("lat")
        lon = sel.get("lon")
        admin = sel.get('admin')

        # попытка поиска по city + country_code
        if lat is None or lon is None:
            try:
                geo_data = geo_coding_request(city=city, country_code=country_code)
                lat, lon = geo_data.get('latitude'), geo_data.get('longitude')
            except GeoApiException as e:
                context['error'] = str(e)
                return render(request, 'weather_search/search.html', context)
    # Ветка с сырыми данными
    else:
        try:
            # Поиск по города по истории поиска городов
            if extracted_get_parameters.get('history'):
                geo_data = geo_coding_request(city=raw_city, admin=extracted_get_parameters.get('admin'))

            # Попытка поиска по сырой строке города
            else:
                geo_data = geo_coding_request(city=raw_city)

        except GeoApiException as e:
            context['error'] = str(e)
            return render(request, 'weather_search/search.html', context)

        lat, lon = geo_data.get('latitude'), geo_data.get('longitude')
        country, country_code, city, admin = (
            geo_data.get('country'),
            geo_data.get('country_code'),
            geo_data.get('name'),
            geo_data.get('admin1')
        )

    context['city_name'] = city
    context['latitude'] = lat
    context['longitude'] = lon
    context['country'] = country
    context['admin'] = admin
    context['country_code'] = country_code

    # Валидация значения forecast_days
    forecast_days, error = validate_forecast_days(request.GET.get('forecast_days'))
    if error:
        context['error'] = error
        return render(request, "weather_search/search.html", context)

    context['forecast_days'] = forecast_days

    # запрос к Open Meteo
    client = openmeteo_requests.Client()
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "rain",
            "is_day"
        ],
        "hourly": [
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "rain",
            "is_day",
            "wind_speed_10m"
        ],
        "timezone": "auto",
        "forecast_days": forecast_days,
    }

    # словарь с данными о найденном городе
    city_values_dict = {
        k: v
        for k, v in context.items()
        if k in SEARCH_FIELDS
    }

    city_values_dict.update({'city': context['city_name']})

    # Добавление найденного города в историю авторизованного или неавторизованного пользователя

    # Для неавторизованного пользователя
    if not request.user.is_authenticated:
        # Добавление нового города к session
        CityHistoryContextService.add_city_to_session_history(
            session=request.session,
            city_values_dict=city_values_dict
        )

        # Добавление истории в БД
        CityHistoryContextService.save_anonymous_city_history(city_values_dict=city_values_dict)
    else:
        # Добавление нового города к текущему user
        created = add_history_city_to_user(
            user=request.user,
            city_values_dict=city_values_dict
        )

        # Если объект HistoryModel не создан, то нужно всё равно его учесть в БД, для отобржения в total-city-searched/
        if not created:
            CityHistoryContextService.save_anonymous_city_history(city_values_dict=city_values_dict)

    responses = client.weather_api(url, params=params)
    response = responses[0]

    tz_raw = response.Timezone()
    if isinstance(tz_raw, bytes):
        tz_name = tz_raw.decode('utf-8', errors='replace')
    else:
        tz_name = str(tz_raw)

    # Создание объекта зоны
    try:
        tz = ZoneInfo(tz_name)
    except Exception as e:
        raise RuntimeError(f"Не удалось создать ZoneInfo для '{tz_name}': {e}")

    # Формирование current_weather в context
    current = response.Current()

    current_weather_data = {}
    for name, (idx, func) in VARIABLES_CURRENT.items():
        processor = func if func else (lambda x: x)
        current_weather_data[name] = processor(current.Variables(idx).Value())

    context["current_weather"] = current_weather_data

    # Формирование hourly_by_day в context
    hourly = response.Hourly()
    length = hourly.Variables(1).ValuesLength()

    start_time = hourly.Time()
    interval = hourly.Interval()

    # hourly_date содержит в себе всю почасовую информацию о погоде
    hourly_data = {}
    for name, (idx, func) in VARIABLES_HOURLY.items():
        processor = func if func else (lambda x: x)
        hourly_data[name] = [
            processor(hourly.Variables(idx).Values(i))
            for i in range(length)
        ]

    local_time = datetime.now(tz=tz)
    rounded_local = local_time.replace(minute=0, second=0, microsecond=0)

    grouped_by_day = defaultdict(list)
    for i in range(length):
        current_hour = datetime.fromtimestamp(start_time + i * interval, tz=tz)
        current_date = current_hour.date()

        # Фильтрация hourly_date таким образом,
        # чтобы погода показывалась с местного времени города, в который сделали запрос
        if current_hour < rounded_local:
            continue

        filtered_hourly_data = {}
        for name in VARIABLES_HOURLY.keys():
            filtered_hourly_data[name] = hourly_data[name][i]

        filtered_hourly_data['time'] = current_hour.strftime('%Y-%m-%d %H:%M')

        grouped_by_day[current_date].append(filtered_hourly_data)
    context['hourly_by_day'] = dict(grouped_by_day)

    return render(request, 'weather_search/search.html', context)
