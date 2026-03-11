from django.urls import path

from . import views


urlpatterns = [
    path('', views.latest_readings, name='latest_readings'),
    path('api/ingest/', views.ingest_reading, name='ingest_reading'),
]
