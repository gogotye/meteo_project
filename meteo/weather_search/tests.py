import json
import requests
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, MagicMock, ANY
from .utils import (mock_geocoding_api_request, mock_current_data,
                    mock_hourly_variables_test, mock_timestamp, expected_hour_rows)
import random


class WeatherViewTest(TestCase):
    def test_get_request_return_correct_response(self):
        response = self.client.get(reverse('weather_search:search'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'weather_search/search.html')
        self.assertContains(response, '<form')
        self.assertContains(response, 'Введите название города')
        self.assertContains(response, '<input id="city-input"')
        self.assertContains(response, '<input type="number" name="forecast_days"')
        self.assertContains(response, '<input type="hidden" id="city-selection"')
        self.assertContains(response, '<button type="submit">Найти</button>')

    def test_get_response_with_empty_city(self):
        response_1 = self.client.get(reverse('weather_search:search'), {
            'city': '',
            'forecast_days': '3',
        })

        self.assertEqual(response_1.status_code, 200)
        self.assertContains(response_1, 'Нужно ввести название города!')

        response_2 = self.client.get(reverse('weather_search:search'), {
            'forecast_days': '3',
        })

        self.assertEqual(response_2.status_code, 200)
        self.assertContains(response_2, 'Нужно ввести название города!')

    def test_get_response_with_incorrect_city_name(self):
        response = self.client.get(reverse('weather_search:search'), {
            'city': 'safgre21',
            'forecast_days': '3',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Город не найден')

    def test_no_weather_table_when_city_not_found(self):
        response = self.client.get(reverse('weather_search:search'), {
            'city': 'safgre21',
            'forecast_days': '3',
        })
        self.assertNotContains(response, '<h2 class="center">Результат</h2>')
        self.assertNotContains(response, '<h3>Почасовой прогноз</h3>')
        self.assertNotContains(response, '<table')

    def test_get_response_with_empty_forecast_days(self):
        response = self.client.get(reverse('weather_search:search'), {
            'city': 'Москва',
            'forecast_days': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-forecast-days="3"')

    def test_get_response_includes_current_weather(self):
        response = self.client.get(reverse('weather_search:search'), {
            'city': 'Москва',
            'forecast_days': '3',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h3>Текущая погода</h3>')

    def test_get_response_includes_hourly_table_with_weather(self):
        response = self.client.get(reverse('weather_search:search'), {
            'city': 'Москва',
            'forecast_days': '3',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<h3>Почасовой прогноз</h3>")
        self.assertContains(response, '<table class="weather-table">')

    @patch('weather_search.utils.requests.get')
    def test_geolocation_api_failure(self, mock_get):
        mock_get.return_value.raise_for_status.side_effect = requests.HTTPError

        response = self.client.get(reverse('weather_search:search'), {
            'city': 'Москва',
            'forecast_days': '3',
        })

        self.assertContains(response, 'Ошибка при запросе геоданных')

    @patch('weather_search.utils.requests.get')
    def test_geolocation_json_incorrect(self, mock_get):
        mock_get.return_value.json.side_effect = json.JSONDecodeError('err', "()", 0)

        response = self.client.get(reverse('weather_search:search'), {
            'city': 'Москва',
            'forecast_days': '3',
        })

        self.assertContains(response, 'Некорректный ответ от геосервиса')

    def test_forecast_days_normal_values(self):
        for value in [1, 16, 5]:
            with self.subTest(forecast_days=value):
                response = self.client.get(reverse('weather_search:search'), {
                    'city': 'Москва',
                    'forecast_days': value,
                })
                self.assertContains(response, "<strong>Город:</strong> Москва")
                self.assertContains(response, "<h3>Текущая погода</h3>")
                self.assertContains(response, "<h3>Почасовой прогноз</h3>")

    def test_forecast_days_below_minimum(self):
        for value in [-5, 0]:
            with self.subTest(forecast_days=value):
                response = self.client.get(reverse('weather_search:search'), {
                    'city': 'Москва',
                    'forecast_days': value,
                })
                self.assertContains(response, "Введите корректное количество дней (от 1 до 16)")

    def test_get_response_with_forecast_days_more_than_max(self):
        for value in [20, 17]:
            with self.subTest(forecast_days=value):
                response = self.client.get(reverse('weather_search:search'), {
                    'city': 'Москва',
                    'forecast_days': value,
                })
                self.assertContains(response, "Введите корректное количество дней (от 1 до 16)")

    def test_get_response_tables(self):
        random_days_from_one_to_five = random.randint(1, 5)
        response = self.client.get(reverse('weather_search:search'), {
            'city': 'Москва',
            'forecast_days': random_days_from_one_to_five,
        })
        self.assertContains(response, '<table class="weather-table">', count=random_days_from_one_to_five)

    def test_forecast_days_with_non_numeric_value(self):
        response = self.client.get(reverse('weather_search:search'), {
            'city': 'Москва',
            'forecast_days': 'abc',
        })
        self.assertContains(response, "Введите корректное количество дней (от 1 до 16)")

    def test_history_city_appears(self):

        session = self.client.session
        session['city_history'] = [
            {'city': 'Москва', 'forecast_days': 3},
            {'city': 'Владивосток', 'forecast_days': 1},
        ]
        session.save()

        response = self.client.get(reverse('weather_search:search'))

        self.assertContains(response, '<h2 class="center">История запросов</h2>')
        self.assertContains(response, 'Москва')
        self.assertContains(response, '3')
        self.assertContains(response, 'Владивосток')
        self.assertContains(response, '1')
        self.assertContains(response, '<li data-history-city>',
                            count=len(session['city_history']))


class WeatherForecastMockTest(TestCase):
    @patch('weather_search.views.openmeteo_requests.Client.weather_api')
    @patch('weather_search.utils.requests.get')
    def test_forecast_with_mocked_api_renders_two_days(self, mock_get, mock_weather_api):

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_geocoding_api_request()

        fake_response = MagicMock()
        fake_response.Timezone.return_value = 'Europe/Moscow'

        fake_current = MagicMock()
        fake_current.Variables.side_effect = mock_current_data
        fake_response.Current.return_value = fake_current

        fake_hourly = MagicMock()
        fake_hourly.Variables.side_effect = mock_hourly_variables_test
        fake_hourly.Time.return_value = mock_timestamp()
        fake_hourly.Interval.return_value = 3600
        fake_response.Hourly.return_value = fake_hourly

        mock_weather_api.return_value = [fake_response]

        forecast_days = 2
        response = self.client.get(reverse('weather_search:search'), {
            'city': 'Москва',
            'forecast_days': forecast_days,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<table class="weather-table">', count=forecast_days)
        self.assertContains(response, '<strong>Город:</strong> Москва')
        self.assertContains(response, 'Текущая погода')
        self.assertContains(response, 'Почасовой прогноз')
        self.assertContains(response, '<tr data-hour-row>', count=expected_hour_rows(forecast_days=forecast_days))

        mock_get.assert_called_once_with(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                'name': 'Москва',
                'count': 5,
                'language': 'ru',
                'countryCode': None
            }
        )

        mock_weather_api.assert_called_with(
            'https://api.open-meteo.com/v1/forecast',
            params=ANY
        )
