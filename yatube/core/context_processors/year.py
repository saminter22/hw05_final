from datetime import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    current_datetime = datetime.now()
    return {
        'year': current_datetime.year
    }
