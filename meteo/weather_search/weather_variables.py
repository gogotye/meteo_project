from .utils_basic import safe_round


VARIABLES_CURRENT = {
    "temperature": (0, safe_round),
    "apparent_temperature": (1, safe_round),
    "humidity": (2, None),
    "rain": (3, safe_round),
    "is_day": (4, None),
}


VARIABLES_HOURLY = {
    "temperature": (0, safe_round),
    "apparent_temperature": (1, safe_round),
    "humidity": (2, None),
    "rain": (3, safe_round),
    "is_day": (4, None),
    "wind_speed": (5, safe_round),
}

SEARCH_FIELDS = ['city', 'country', 'country_code', 'admin', 'forecast_days']
