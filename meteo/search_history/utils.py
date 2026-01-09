from .models import HistoryModel


def add_history_city_to_user(user, city_values_dict):
    """Добавляет новый объект HistoryModel с указанным user в БД"""

    obj, created = HistoryModel.objects.get_or_create(user=user, **city_values_dict)
    return created
