import re


def is_cyrillic(text):
    """Проверяет строку на наличие символов русского алфавита, если найден - ворвращает True"""

    a = bool(re.search(r'[А-Яа-яЁё]', text))
    return a
