def safe_round(value, digits=2):
    "Округляет значение, если оно числовое (float или int)."

    try:
        return round(value, digits)
    except (TypeError, ValueError):
        return value
