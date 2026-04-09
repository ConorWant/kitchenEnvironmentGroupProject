from django.urls import path

from . import views

app_name = "monitor"

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("history/", views.history_view, name="history"),
    path("management/", views.management_view, name="management"),
    path("live-dashboard/", views.live_dashboard_view, name="live_dashboard"),
]
