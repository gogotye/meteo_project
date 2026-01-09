FROM python:3.12-slim

WORKDIR /django-app

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


COPY meteo .


CMD sh -c "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"